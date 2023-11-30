from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import hack.routing

print("HERE")
application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
        URLRouter(
            hack.routing.websocket_urlpatterns
        )
    ),
})
