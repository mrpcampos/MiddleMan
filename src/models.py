from app import db


class Client(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    cpf = db.Column(db.String())
    full_name = db.Column(db.String())
    birthdate = db.Column(db.Date())
    email = db.Column(db.String())
    phone = db.Column(db.String())
    liquid_salary = db.Column(db.Float())
    offers = db.relationship('Offer', lazy="dynamic")


class Offer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_client = db.Column(db.Integer(), db.ForeignKey('client.id'))
    expiration_date = db.Column(db.DateTime())
    partner_id = db.Column(db.Integer())
    partner_name = db.Column(db.String())
    value = db.Column(db.Float())
    installments = db.Column(db.Integer())
    tax_rate_percent_montly = db.Column(db.Float())
    total_value = db.Column(db.Float())

    @property
    def serialize(self, ):
        return {
            "expiration_date": self.expiration_date,
            "partner_id": self.partner_id,
            "partner_name": self.partner_name,
            "value": self.value,
            "installments": self.installments,
            "tax_rate_percent_montly": self.tax_rate_percent_montly,
            "total_value": self.total_value
        }


class Proposal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_client = db.Column(db.Integer(), db.ForeignKey('client.id'))
    endpoint_proposal_id = db.Column(db.Integer())
    creation_date = db.Column(db.DateTime())
    accepted = db.Column(db.Boolean())
    client_cpf = db.Column(db.String())
    client_full_name = db.Column(db.String())
    client_birthdate = db.Column(db.Date())
    client_email = db.Column(db.String())
    client_phone = db.Column(db.String())
    client_liquid_salary = db.Column(db.Float())
    offer_expiration_date = db.Column(db.DateTime())
    offer_partner_id = db.Column(db.Integer())
    offer_partner_name = db.Column(db.String())
    offer_value = db.Column(db.Float())
    offer_installments = db.Column(db.Integer())
    offer_tax_rate_percent_montly = db.Column(db.Float())
    offer_total_value = db.Column(db.Float())
