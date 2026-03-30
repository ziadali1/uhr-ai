"""
Azure Functions v2 entry point — expõe o app FastAPI via HTTP trigger com rota wildcard.
"""
import azure.functions as func
from azure.functions import AsgiMiddleware
from main import app as fastapi_app

# FunctionApp com auth anônimo — a autenticação é feita pelo JWT do Supabase dentro do FastAPI
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.route(route="{*route}")
async def http_trigger(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    return await AsgiMiddleware(fastapi_app).handle_async(req, context)
