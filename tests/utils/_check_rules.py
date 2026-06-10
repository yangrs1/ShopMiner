from app import create_app
from app.models.analytics import AssociationRule

app = create_app()
with app.app_context():
    total = AssociationRule.query.count()
    with_pid = AssociationRule.query.filter(AssociationRule.product_id.isnot(None)).count()
    with_cid = AssociationRule.query.filter(AssociationRule.consequent_id.isnot(None)).count()
    print(f'Total rules: {total}')
    print(f'With product_id: {with_pid}')
    print(f'With consequent_id: {with_cid}')
    sample = AssociationRule.query.filter(AssociationRule.product_id.isnot(None)).first()
    if sample:
        print(f'Sample: {sample.antecedent} -> {sample.consequent} (pid={sample.product_id}, cid={sample.consequent_id})')
