from app import app, db, Cupcake

with app.app_context():
    cupcakes = Cupcake.query.all()
    print(f"Total de cupcakes: {len(cupcakes)}")
    for c in cupcakes:
        print(c.sabor, c.preco)
