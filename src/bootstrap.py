import uvicorn

from zjbs_file_server.settings import settings

if __name__ == "__main__":
    listen_host, listen_port = settings.LISTEN_ADDRESS.split(":")
    uvicorn.run("zjbs_file_server.app:app", host=listen_host, port=int(listen_port), reload=settings.DEBUG_MODE)
