#!/usr/bin/env python3
import os
import json
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_elasticache as elasticache,
    aws_rds as rds,
    aws_s3 as s3,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as apigwv2_integrations,
    aws_iam as iam,
    RemovalPolicy,
    CfnOutput,
    Duration
)
from constructs import Construct

class TtbLabelComplianceStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, env_name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Load Configuration
        config_path = os.path.join(os.path.dirname(__file__), "deployment_config.json")
        with open(config_path, "r") as f:
            all_configs = json.load(f)
        config = all_configs.get(env_name, all_configs.get("default", {}))

        # 1. VPC
        vpc = ec2.Vpc(self, f"Vpc-{env_name}", max_azs=config.get("vpc_max_azs", 2))

        # 2. S3 Buckets
        bucket = s3.Bucket(
            self, f"JobsBucket-{env_name}",
            removal_policy=RemovalPolicy.DESTROY, # Only safe if empty
            auto_delete_objects=True # CDK native auto-delete
        )

        frontend_bucket = s3.Bucket(
            self, f"FrontendBucket-{env_name}",
            website_index_document="index.html",
            website_error_document="index.html",
            public_read_access=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ACLS,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # 3. RDS (PostgreSQL)
        db_security_group = ec2.SecurityGroup(self, f"DbSg-{env_name}", vpc=vpc)
        db = rds.DatabaseInstance(
            self, f"JobsDb-{env_name}",
            engine=rds.DatabaseInstanceEngine.postgres(version=rds.PostgresEngineVersion.VER_15),
            instance_type=ec2.InstanceType.of(
                getattr(ec2.InstanceClass, config.get("rds_instance_class", "T3")), 
                getattr(ec2.InstanceSize, config.get("rds_instance_size", "MICRO"))
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[db_security_group],
            removal_policy=RemovalPolicy.DESTROY,
            deletion_protection=False,
            database_name="jobsdb",
            backup_retention=Duration.days(0)
        )

        # 4. ElastiCache (Redis)
        redis_security_group = ec2.SecurityGroup(self, f"RedisSg-{env_name}", vpc=vpc)
        subnet_group = elasticache.CfnSubnetGroup(
            self, f"RedisSubnetGroup-{env_name}",
            description=f"Subnet group for Redis {env_name}",
            subnet_ids=[subnet.subnet_id for subnet in vpc.private_subnets]
        )
        redis = elasticache.CfnCacheCluster(
            self, f"RedisCluster-{env_name}",
            cache_node_type=config.get("redis_node_type", "cache.t3.micro"),
            engine="redis",
            num_cache_nodes=1,
            cache_subnet_group_name=subnet_group.ref,
            vpc_security_group_ids=[redis_security_group.security_group_id]
        )

        # 5. ECS Cluster
        cluster = ecs.Cluster(self, f"Cluster-{env_name}", vpc=vpc)

        # Build Image
        image = ecs.ContainerImage.from_asset(
            "../../",
            file="Dockerfile.backend",
            exclude=["deploy/aws/cdk.out", "node_modules", ".git", "__pycache__"]
        )

        # Environment Variables
        db_url = f"postgresql://{db.secret.secret_value_from_json('username').unsafe_unwrap()}:{db.secret.secret_value_from_json('password').unsafe_unwrap()}@{db.db_instance_endpoint_address}:5432/{db.secret.secret_value_from_json('dbname').unsafe_unwrap()}"
        redis_url = f"redis://{redis.attr_redis_endpoint_address}:{redis.attr_redis_endpoint_port}/0"
        
        environment = {
            "DATABASE_URL": db_url,
            "REDIS_URL": redis_url,
            "S3_BUCKET_PATH": f"{bucket.bucket_name}/jobs/",
            "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", "dummy"),
            "ENVIRONMENT": env_name
        }

        # 6. Backend API (ALB Fargate Service)
        api_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, f"ApiService-{env_name}",
            cluster=cluster,
            cpu=config.get("ecs_api_cpu", 512),
            memory_limit_mib=config.get("ecs_api_memory", 1024),
            desired_count=1,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=image,
                container_port=8000,
                environment=environment
            ),
            public_load_balancer=True,
            runtime_platform=ecs.RuntimePlatform(
                cpu_architecture=ecs.CpuArchitecture.ARM64,
                operating_system_family=ecs.OperatingSystemFamily.LINUX,
            )
        )

        # 7. Celery Worker (Fargate Service)
        worker_task_def = ecs.FargateTaskDefinition(
            self, f"WorkerTaskDef-{env_name}",
            cpu=config.get("ecs_worker_cpu", 512),
            memory_limit_mib=config.get("ecs_worker_memory", 1024),
            runtime_platform=ecs.RuntimePlatform(
                cpu_architecture=ecs.CpuArchitecture.ARM64,
                operating_system_family=ecs.OperatingSystemFamily.LINUX,
            )
        )
        worker_task_def.add_container(
            f"WorkerContainer-{env_name}",
            image=image,
            command=["celery", "-A", "src.backend.worker.celery_app", "worker", "--loglevel=info"],
            environment=environment,
            logging=ecs.LogDrivers.aws_logs(stream_prefix="Worker")
        )
        worker_service = ecs.FargateService(
            self, f"WorkerService-{env_name}",
            cluster=cluster,
            task_definition=worker_task_def,
            desired_count=1
        )

        # Permissions
        bucket.grant_read_write(api_service.task_definition.task_role)
        bucket.grant_read_write(worker_task_def.task_role)
        
        # Security Group Ingress
        db_security_group.add_ingress_rule(api_service.service.connections.security_groups[0], ec2.Port.tcp(5432))
        db_security_group.add_ingress_rule(worker_service.connections.security_groups[0], ec2.Port.tcp(5432))
        redis_security_group.add_ingress_rule(api_service.service.connections.security_groups[0], ec2.Port.tcp(6379))
        redis_security_group.add_ingress_rule(worker_service.connections.security_groups[0], ec2.Port.tcp(6379))

        # Auto Scaling
        scalable_api = api_service.service.auto_scale_task_count(max_capacity=5)
        scalable_api.scale_on_cpu_utilization("CpuScaling", target_utilization_percent=70)

        scalable_worker = worker_service.auto_scale_task_count(max_capacity=5)
        scalable_worker.scale_on_cpu_utilization("WorkerCpuScaling", target_utilization_percent=70)

        # 8. API Gateway (HTTP API) for Default HTTPS
        http_api = apigwv2.HttpApi(
            self, f"HttpApiGateway-{env_name}",
            default_integration=apigwv2_integrations.HttpAlbIntegration(
                f"AlbIntegration-{env_name}",
                api_service.listener,
            )
        )

        CfnOutput(self, "ApiGatewayUrl", value=http_api.api_endpoint)
        CfnOutput(self, "AlbDnsName", value=api_service.load_balancer.load_balancer_dns_name)
        CfnOutput(self, "JobsBucketName", value=bucket.bucket_name)
        CfnOutput(self, "FrontendBucketName", value=frontend_bucket.bucket_name)
        CfnOutput(self, "FrontendWebsiteUrl", value=frontend_bucket.bucket_website_url)

app = cdk.App()
env_name = app.node.try_get_context("env_name") or "dev"
stack = TtbLabelComplianceStack(app, f"TtbLabelComplianceStack-{env_name}", env_name=env_name)

# Add cost tracking tag to all resources in the stack
cdk.Tags.of(app).add("AppManagerCFNStackKey", f"TtbLabelComplianceStack-{env_name}")

app.synth()
