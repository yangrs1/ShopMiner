from app import create_app
from app.models.product import Product
from app.models.analytics import AssociationRule

app = create_app()
with app.app_context():
    rules = AssociationRule.query.limit(5).all()
    for r in rules:
        if r.antecedent and not r.antecedent.startswith('[StockCode]'):
            desc = r.antecedent.split(',')[0].strip()
            product = Product.query.filter(Product.description.like(f'%{desc}%')).first()
            if product:
                print(f'Test product: id={product.id} desc="{product.description[:50]}"')
                break
