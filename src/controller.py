from flask import request, Blueprint, jsonify
from sqlalchemy import func
from datetime import datetime, timedelta

from jsonschema import validate
import jsonschema
import yaml
import json
import os

import requests
app = Blueprint('', __name__)

from models import Client, Offer, Proposal
from app import db

# carregando os modelos de json que esperamos receber
with open('client-schema.json') as file:
    client_schema = json.loads(file.read())
with open('proposal-schema.json') as file:
    proposal_schema = json.loads(file.read())
with open('offers-schema.json') as file:
    offers_schema = json.loads(file.read())

# Carregando arquivo de configurações
with open(os.environ['MIDDLEMAN_CONFIG']) as f:
    config_file = yaml.safe_load(f)

# Em uma aplicação em produção essa variável viria de um arquivo de configurações, para fácil alteração
_offer_duration = config_file['offer_duration_minutes']
_proposal_min_interval = config_file['proposal_minimal_days_interval']


@app.route('/')
def hello_world():
    return 'Server funcionando!'


@app.route('/offers', methods=['POST'])
def get_offers():
    # Começamos testando se o pedido esta correto
    try:
        client_json = request.get_json(force=True)
        validate(client_json, client_schema)
    except jsonschema.ValidationError:
        return "Invalid Json, validate it with the proper schema before making the request.", 400

    client_query = Client.query.filter_by(cpf=client_json['cpf'])
    client = client_query.first()
    # Checamos se já temos as ofertas desse cliente
    if client:
        offers = client.offers.filter(Offer.expiration_date > func.current_timestamp())
        offers = offers.all()
        # Caso ja tenhamos as ofertas retornamos elas
        if offers:
            offers = {'offers': [offer.serialize for offer in offers]}
            return jsonify(offers)

    # Pedimos por novas ofertas
    # Devo resaltar que o client_json foi validado acima, logo sabemos que tem a correta formatação
    response = requests.post("https://644ceee6-245b-4ac5-bb10-7f9995b0a9a9.mock.pstmn.io/offers", client_json)

    # Se a requisição foi um sucesso
    if response.ok:
        try:
            offers = response.json()
            validate(offers, offers_schema)
            offers = offers['offers']
        except ValueError as e:
            print(e)
            return "Failed to comunicate properly with remote provider. ", 503
        except jsonschema.ValidationError as e:
            print(e)
            return "Failed to comunicate properly with remote provider. Received files on won't match schema.", 503

        # Salvamos os dados do cliente (e damos flush, gerando o id)
        if client:
            client_query.update(client_json, synchronize_session=False)
        else:
            client = Client(**client_json)
            db.session.add(client)
        db.session.flush()

        # Salvamos os dados da oferta, incluindo a referência ao cliente e data de expiração
        base_info = {"id_client": client.id,
                     "expiration_date": func.current_timestamp() + timedelta(minutes=_offer_duration)}
        new_offers = []
        for offer in offers:
            new_offer = Offer(**base_info, **offer)
            db.session.add(new_offer)
            new_offers.append(new_offer)
        db.session.commit()
        offers = {'offers': [offer.serialize for offer in new_offers]}
        return jsonify(offers)

    # Caso não consigamos contatar o servidor
    return "Cant comunicate to remote provider.", 503


@app.route('/proposal', methods=['POST'])
def make_proposal():
    # Começamos testando se o pedido esta correto
    try:
        proposal_json = request.get_json(force=True)
        validate(proposal_json, proposal_schema)
    except jsonschema.ValidationError:
        return "Invalid Json, validate it with the proper schema before making the request.", 400

    # Separamos os elementos da proposta recebida
    received_proposal = proposal_json['proposal']
    received_client = received_proposal['client']
    received_offer = received_proposal['offer']

    # Recuperamos o cliente relacionado a proposta
    client_query = Client.query.filter_by(cpf=received_client['cpf'])
    know_client = client_query.first()
    # Verificamos se há alterações em informações cruciais do cliente, aceitamos apenas alterações de email e telefone
    if not (know_client and client_sensitive_fields_match(received_client, know_client)):
        return "Invalid Proposal, Client's information invalid.", 400

    # Verificamos se a oferta escolhida é válida (existe / não expirou / não foi alterada)
    offer = Offer.query.filter_by(id_client=know_client.id) \
        .filter(Offer.expiration_date > func.current_timestamp()) \
        .filter_by(**received_offer)
    offer = offer.first()
    if not offer:
        return "Invalid offer, maybe it expired?", 404

    # Sendo a oferta válida procuramos propostas duplicadas
    # Definimos duplicatas comos propostas com o mesmo cliente e parceiro, dentro do intervalo definido
    existing_proposal = Proposal.query.filter_by(id_client=know_client.id)\
        .filter_by(offer_partner_id=received_offer['partner_id'])\
        .filter(Proposal.creation_date + timedelta(days=_proposal_min_interval) > func.current_timestamp())\
        .filter_by(accepted=True)
    existing_proposal = existing_proposal.first()
    if existing_proposal:
        # Se foi encontrada uma duplicata enviamos uma mensagem avisando
        return "Proposta já foi enviada e aceita anteriormente.", 206

    # Se o request chegou até aqui a proposta é válida
    # Começamos então a salvar os dados, começando pelas possíveis alterações no cliente (email ou telefone)
    client_query.update(received_client, synchronize_session=False)

    # Então enviamos a proposta
    response = requests.post('https://644ceee6-245b-4ac5-bb10-7f9995b0a9a9.mock.pstmn.io/proposal',
                             proposal_json)
    response_json = response.json()

    # Usamos o código da resposta para saber se foi aprovada ou não
    accepted = response.status_code == 200

    # Preparamos os dados e salvamos no banco de dados
    base_info = {"id_client": know_client.id, "creation_date": func.current_timestamp(), "accepted": accepted}
    if "proposal_id" in response_json:
        base_info['endpoint_proposal_id'] = response_json["proposal_id"]
    client_info = {"client_" + k: v for k, v in received_client.items()}
    offer_info = {"offer_" + k: v for k, v in received_offer.items()}
    proposal = Proposal(**base_info, **client_info, **offer_info)
    db.session.add(proposal)
    db.session.commit()
    if accepted:
        return "Proposal Approved!", 200
    else:
        return "Proposal Refused.", 403


def client_sensitive_fields_match(received_client, know_client: Client):
    same_birth = datetime.combine(know_client.birthdate, datetime.min.time()) == datetime.fromisoformat(
        received_client['birthdate'])
    same_salary = int(know_client.liquid_salary) == received_client['liquid_salary']
    same_name = know_client.full_name == received_client['full_name']
    return same_birth and same_salary and same_name
