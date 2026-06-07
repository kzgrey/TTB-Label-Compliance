#!/usr/bin/env zsh
set -e

# Get repo root relative to the script
SCRIPT_DIR="${0:A:h}"
REPO_ROOT="${SCRIPT_DIR:h}"

# Ensure a TTBID was provided
if [ -z "$1" ]; then
  echo "Error: TTBID is required."
  echo "Usage: $0 <TTBID>"
  exit 1
fi

TTBID=$1
DATA_DIR="$REPO_ROOT/data/$TTBID"

# Make sure data and target directory exists
mkdir -p "$DATA_DIR"

HTML_FILE="$DATA_DIR/index.html"

# Define the exact curl header arguments to be reused across all calls, matching the browser exactly
CURL_HEADERS=(
  -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7'
  -H 'Accept-Language: en-US,en;q=0.9'
  -H 'Cache-Control: no-cache'
  -H 'Connection: keep-alive'
  -b 'JSESSIONID="1AN8rJvlGscoMTXSlx516pxEMPtMRCeRkrak6Cf8.master:colas-ext-server"; TS0128ecc9=0134890737881dfc09f1d7e9f327c7f8c30ff831a923bf7cf3b02d3e3a84333c66803486c94ca9afb58aa65ca1e4e402d11c92ebb535ae5dbe2255aa763f94f912d0248f00; TS01289f9a=01f6e3b1e98997c649ad51821e444bf00203703f00b9a91d2ea72a16b0012b51da9657803cca94afd9cd35e2a33a4dc10dfa2571981fb2174014805d218e8760702f8ce5d930e3cb37b9b72f476ca108f290d5e0b2; _ga=GA1.1.1009602374.1780441074; BIGipServerCOLAS_PROD_POOL=1408082442.39462.0000; BIGipServeruc+jAW63kG3h06BOJF04fg=!eqY9k8UzhtXGDY/7JBugub3RY/6xtBwSwol/WxP6UuiYhhJo2zPDOG1TZlqUqUoUUnKxaxkkKMpYpA==; _ga_CSLL4ZEK4L=GS2.1.s1780771777$o5$g1$t1780771950$j60$l0$h0; TS83de0437029=08e9798694ab2800bbf9dac68f9ba2b86467ac9abbbd35d52a847e6ccef8ad58a688487f1367b6bd99405f472045cabf; TSPD_101=08e9798694ab280078734bb83e7a16ca45464c2f55dd0104f64df1e0e204881314c4875cd99d7ae9dfc01d3c801a372808d6a5a91c051800133d1d6db285cc898f305b118389ee0620c71334e42bd955; TS01f7a357=0134890737dc24a547886b3874a71439297379c39263691f6d8c58e492fb847be5a3b0d71d6189e245e515ddff6807e574c0d50aac; TS012277fa=01f6e3b1e920a669194ef5aeb86816f8e54b8792a9b9a91d2ea72a16b0012b51da9657803cb965cbc59953f6a9ba3ef4126d24d4c6e306838890d819feac5c32e822c11a01; TS646cb979027=08e9798694ab2000d783b8d4f6f27fa752493d7d551e6f959b165908141e7e8dae23aaf3585b0f51084e086c1f113000bfe1eb902d9e42208623d76d74d64d55c43288bb40dff65243fdadee7f9d8927739926a5aa59782bec6fc2d4743d3cb9; TS017ec985=01f6e3b1e9a0d0a3550295f778013bf9f9eb179f2443f444f7cb7bd45e86c6f34c5083ceb362a21d4f36a7ea46bbc377a84323e0e6bbb37beb42589b8bb5d51eac272efc70eb43838bc7d550039f083596786ae2bc92edc1f44a42bd5f8ce1de45b574b83f9d95db0838fdcc91b14bbd7d5c3818de01114847e7e89f4784bcb17b4ebad2e9; TS83de0437077=08e9798694ab28002b99dc1373d2da2e4e29e068c16d3364d063b95841a0a8a4ba285978bab7a31493e0eff89a3274f708623bf5fb172000aa50f24c492a1237e49aeae36ec2421240b4c89a38e70f36a6471483ff608ec7'
  -H 'Pragma: no-cache'
  -H 'Sec-Fetch-Dest: document'
  -H 'Sec-Fetch-Mode: navigate'
  -H 'Sec-Fetch-Site: none'
  -H 'Sec-Fetch-User: ?1'
  -H 'Upgrade-Insecure-Requests: 1'
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36'
  -H 'sec-ch-ua: "Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"'
  -H 'sec-ch-ua-mobile: ?0'
  -H 'sec-ch-ua-platform: "macOS"'
)

echo "=== STEP 1: DOWNLOADING DETAILS PAGE ==="
echo "Target URL: https://ttbonline.gov/colasonline/viewColaDetails.do?action=publicFormDisplay&ttbid=${TTBID}"

# Perform verbose curl download
curl -v -k "https://ttbonline.gov/colasonline/viewColaDetails.do?action=publicFormDisplay&ttbid=${TTBID}" \
  "${CURL_HEADERS[@]}" \
  -o "$HTML_FILE"

# Extract unique image src URLs from <img> tags using perl (split by newline to handle spaces inside src values)
# The Zsh (f) flag splits the command output by newline only.
urls=("${(f)$(perl -ne 'while(/<img\s+[^>]*src=["\x27]([^"\x27]*)["\x27]/gi) { print "$1\n"; }' "$HTML_FILE" | sort -u)}")

echo "=== STEP 2: DOWNLOADING EMBEDDED IMAGES ==="
echo "Found ${#urls[@]} unique image URL candidate(s) in HTML."

img_counter=0
for url in "${urls[@]}"; do
  if [ -z "$url" ]; then
    continue
  fi

  # Ignore the publicViewSignature image completely
  if [[ "$url" == *publicViewSignature* ]]; then
    echo "Skipping signature image: $url"
    continue
  fi

  # Resolve absolute URL
  if [[ "$url" == http* ]]; then
    abs_url="$url"
  elif [[ "$url" == //* ]]; then
    abs_url="https:$url"
  elif [[ "$url" == /* ]]; then
    abs_url="https://ttbonline.gov$url"
  else
    abs_url="https://ttbonline.gov/colasonline/$url"
  fi

  # Percent-encode literal spaces in the resolved URL (Zsh parameter substitution)
  abs_url_encoded="${abs_url// /%20}"
  # Replace literal non-breaking spaces with percent codes as well
  abs_url_encoded="${abs_url_encoded//$'\xc2\xa0'/%C2%A0}"
  abs_url_encoded="${abs_url_encoded//$'\xa0'/%A0}"

  echo "--------------------------------------------------"
  echo "DEBUG: Image candidate details:"
  echo "  Original src:     $url"
  echo "  Resolved URL:     $abs_url"
  echo "  Encoded URL:      $abs_url_encoded"

  img_counter=$((img_counter + 1))
  temp_file="$DATA_DIR/temp_img_download"

  # Sleep briefly between requests
  sleep 0.5

  echo "DEBUG: Executing verbose curl command..."
  # Download image using the exact same headers and verbose logging
  http_code=$(curl -v -k "$abs_url_encoded" \
    "${CURL_HEADERS[@]}" \
    -o "$temp_file" \
    -w "%{http_code}")

  echo "DEBUG: Curl result code: $?, HTTP Status: $http_code"

  # Determine file mime-type using file command on macOS
  mime_type=$(file -b --mime "$temp_file")
  echo "DEBUG: File command output: $mime_type"

  # Detect image extension
  ext=""
  if [[ "$mime_type" == *"image/jpeg"* || "$mime_type" == *"image/jpg"* ]]; then
    ext=".jpg"
  elif [[ "$mime_type" == *"image/png"* ]]; then
    ext=".png"
  elif [[ "$mime_type" == *"image/gif"* ]]; then
    ext=".gif"
  elif [[ "$mime_type" == *"image/svg+xml"* ]]; then
    ext=".svg"
  else
    # Fallback to URL path extension
    url_path=$(echo "$abs_url_encoded" | cut -d'?' -f1)
    url_ext="${url_path##*.}"
    if [[ "$url_ext" != "$url_path" && ${#url_ext} -le 4 ]]; then
      ext=".$url_ext"
    else
      ext=".png"
    fi
  fi

  filename="image_${img_counter}${ext}"
  mv "$temp_file" "$DATA_DIR/$filename"
  echo "Saved image to: $DATA_DIR/$filename"

  # Replace original URL with local filename in the HTML file (using environment variables to bypass shell escaping)
  URL="$url" FILENAME="$filename" perl -pi -e 's|\Q$ENV{URL}\E|$ENV{FILENAME}|g' "$HTML_FILE"
  echo "Replaced '$url' with '$filename' in HTML."
done

echo "=================================================="
echo "Successfully completed downloading HTML page and $img_counter image(s) to $DATA_DIR"
