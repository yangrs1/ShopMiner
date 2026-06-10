from app import create_app
from app.models.product import Product
from app.models.analytics import AssociationRule

app = create_app()
with app.app_context():
    # Get a few products
    products = Product.query.filter(Product.is_active == True).limit(3).all()
    for p in products:
        print(f'P[{p.id}] name="{p.name}" desc="{p.description[:60]}"')

    # Check rules
    print()
    rules = AssociationRule.query.limit(3).all()
    for r in rules:
        # Check if any product description matches part of consequent
        products_matching = []
        for p in Product.query.filter(Product.is_active == True).all():
            if p.description and p.description in r.consequent:
                products_matching.append(p.id)
        print(f'Rule: {r.consequent[:60]}')
        print(f'  Products matching: {len(products_matching)}, first 3: {products_matching[:3]}')
