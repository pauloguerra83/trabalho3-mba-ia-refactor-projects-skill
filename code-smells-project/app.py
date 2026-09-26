from src.app import create_app
from src.config.settings import Settings

app = create_app()

if __name__ == "__main__":
    print("=" * 50)
    print("SERVIDOR INICIADO")
    print(f"Rodando em http://{Settings.HOST}:{Settings.PORT}")
    print("=" * 50)

    app.run(host=Settings.HOST, port=Settings.PORT, debug=Settings.DEBUG)
