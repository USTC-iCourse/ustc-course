import openai
import os

if os.getenv("OPENAI_API_KEY"):
    openai.api_key = os.getenv("OPENAI_API_KEY")
else:
    raise ValueError('OPENAI_API_KEY environment variable is not set')

#if os.getenv("HTTP_PROXY"):
#    openai.proxy = os.getenv("HTTP_PROXY")
#else:
#    raise ValueError('HTTP_PROXY environment variable is not set')
