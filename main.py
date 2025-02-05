from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

from schema import schema
from context import get_context


graphql_app = GraphQLRouter(schema, context_getter=get_context)

app = FastAPI()
app.include_router(graphql_app, prefix="/graphql")
