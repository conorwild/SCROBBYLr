from rrecords import create_app

application = create_app()

if __name__ == '__main__':
    application.run(
        host="0.0.0.0",
        port=4999,
        debug=True,
        use_debugger=False,
    )