import logging

class BaseJob:
    """
    Standard Python class framework for defining extensible jobs.
    """
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.logger = logging.getLogger(f"{self.__class__.__name__}_{job_id}")
        self.logger.setLevel(logging.INFO)

    def run(self, *args, **kwargs):
        """
        Execute the job logic. Subclasses must implement this method.
        """
        raise NotImplementedError("Subclasses must implement run()")
