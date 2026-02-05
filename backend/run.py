from app import create_app
app = create_app()
if __name__ == "__main__":
    print("\n" + "="*50)
    print("STARTING SERVER ON ALL INTERFACES (0.0.0.0)")
    print("This is required for mobile devices to connect.")
    print("="*50 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=True)

