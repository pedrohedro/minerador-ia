"""Inicia o Minerador IA: servidor web local + navegador."""
import argparse
import threading
import webbrowser


def main() -> None:
    parser = argparse.ArgumentParser(description="Minerador IA")
    parser.add_argument("--porta", type=int, default=8765)
    parser.add_argument("--sem-navegador", action="store_true")
    parser.add_argument("--autoconectar", action="store_true",
                        help="Conecta ao iniciar, usando a configuração salva")
    parser.add_argument("--iniciar-ia", action="store_true",
                        help="Inicia os palpites da IA após a conexão automática")
    args = parser.parse_args()
    if args.iniciar_ia and not args.autoconectar:
        parser.error("--iniciar-ia exige --autoconectar")

    import uvicorn
    from minerador.server import app, ctrl

    if args.autoconectar:
        ctrl.connect()
        if args.iniciar_ia:
            ctrl.copilot.start()

    url = f"http://127.0.0.1:{args.porta}"
    print(f"Minerador IA rodando em {url}  (feche esta janela para encerrar)")
    if not args.sem_navegador:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host="127.0.0.1", port=args.porta, log_level="warning")


if __name__ == "__main__":
    main()
