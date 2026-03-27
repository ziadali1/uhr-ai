"""
Azure Functions entry point — envolve o app FastAPI para execução serverless.
"""
import azure.functions as func
from main import app
from azure.functions import AsgiMiddleware

handler = AsgiMiddleware(app).handle
