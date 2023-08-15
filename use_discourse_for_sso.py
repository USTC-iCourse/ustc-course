# Copyright 2022
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import os
import secrets
import base64
import hashlib
import hmac
from urllib import parse

# corresponding meta thread:
# https://meta.discourse.org/t/use-discourse-as-an-identity-provider-sso-discourseconnect/32974

# replace with your own secret
SECRET = os.environ['COURSE_DISCOURSE_AS_SSO_PROVIDER_SECRETE']
assert len(SECRET) > 20
SECRET = bytes(SECRET)

# URL to return to after signing on
RETURN_URL = "https://courses.xjtu.live"
# URL to Discourse
DISCOURSE_URL = "https://xjtu.live"


def build_sso_url():
  nonce = secrets.token_urlsafe()

  payload = str.encode("nonce=" + nonce + "&return_sso_url=" + RETURN_URL)

  BASE64_PAYLOAD = base64.b64encode(payload)
  URL_ENCODED_PAYLOAD = parse.quote(BASE64_PAYLOAD)

  sig = hmac.new(SECRET, BASE64_PAYLOAD, hashlib.sha256)
  HEX_SIGNATURE = sig.hexdigest()

  url = DISCOURSE_URL + "/session/sso_provider?sso=" + URL_ENCODED_PAYLOAD + "&sig=" + HEX_SIGNATURE

  return (url, nonce)


def get_sso_response(url, nonce):
  url_params = parse.parse_qs(parse.urlsplit(url).query)

  if "sso" not in url_params:
    return None  # handle error, with "sso" in url
  if "sig" not in url_params:
    return None  # handle error, with "sig" in url

  sso = str.encode(url_params["sso"][0])
  h = hmac.new(SECRET, sso, hashlib.sha256)
  sso_bytes = h.digest()
  sig_bytes = bytes.fromhex(url_params["sig"][0])

  if sso_bytes != sig_bytes:
    return None  # handle error, "sso" disagrees with "sig"

  decoded = base64.b64decode(sso).decode()
  response = parse.parse_qs(decoded)

  if "nonce" not in response or nonce != response["nonce"][0]:
    return None  # handle error, with "nonce"

  return response
