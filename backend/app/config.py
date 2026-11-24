"""Geografia bancária e configuração de simulação GlobalScale."""
from __future__ import annotations
import os
REGIONS = {
    'af': {'name':'África','branches':[('MZ-MPM','Moçambique','Maputo','MZN'),('MZ-BEI','Moçambique','Beira','MZN'),('ZA-JNB','África do Sul','Joanesburgo','ZAR'),('AO-LAD','Angola','Luanda','USD'),('MA-CAS','Marrocos','Casablanca','EUR'),('ST-TMS','São Tomé e Príncipe','São Tomé','EUR'),('SN-DKR','Senegal','Dacar','EUR'),('GH-ACC','Gana','Acra','GHS')]},
    'eu': {'name':'Europa','branches':[('ES-MAD','Espanha','Madrid','EUR'),('PT-LIS','Portugal','Lisboa','EUR'),('FR-PAR','França','Paris','EUR'),('DE-FRA','Alemanha','Frankfurt','EUR'),('GB-LON','Reino Unido','Londres','EUR'),('IT-ROM','Itália','Roma','EUR')]},
    'as': {'name':'Ásia','branches':[('CN-SHA','China','Xangai','CNY'),('CN-BJS','China','Pequim','CNY'),('JP-TYO','Japão','Tóquio','USD'),('IN-MUM','Índia','Mumbai','USD'),('SG-SIN','Singapura','Singapura','USD'),('AE-DXB','Emirados Árabes Unidos','Dubai','USD')]},
    'na': {'name':'América do Norte','branches':[('US-NYC','Estados Unidos','Nova Iorque','USD'),('US-LAX','Estados Unidos','Los Angeles','USD'),('CA-TOR','Canadá','Toronto','USD'),('MX-MEX','México','Cidade do México','USD')]},
    'sa': {'name':'América do Sul','branches':[('BR-SAO','Brasil','São Paulo','USD'),('AR-BUE','Argentina','Buenos Aires','USD'),('CL-SCL','Chile','Santiago','USD'),('CO-BOG','Colômbia','Bogotá','USD')]},
    'oc': {'name':'Oceânia','branches':[('AU-SYD','Austrália','Sydney','USD'),('AU-MEL','Austrália','Melbourne','USD'),('NZ-AKL','Nova Zelândia','Auckland','USD')]}
}
CURRENCIES = ('MZN','EUR','USD','CNY','ZAR','GHS')
# Demonstração: quantas unidades de cada moeda equivalem a 1 EUR.
DEFAULT_EUR_RATES = {'EUR':'1','MZN':'70.11','USD':'1.10','CNY':'7.90','ZAR':'20.00','GHS':'13.50'}
REGION_PORTS = {'af':9501,'eu':9502,'as':9503,'na':9504,'sa':9505,'oc':9506}

def region_url(region):
    return f'https://region-{region}:{REGION_PORTS[region]}'

def branch_details(code):
    for region, details in REGIONS.items():
        for b in details['branches']:
            if b[0] == code:
                return dict(code=b[0], country=b[1], city=b[2], suggested_currency=b[3], region=region)
    return None

def region_config():
    return [{'code':code,'name':meta['name'],'branches':[dict(code=b[0],country=b[1],city=b[2],suggested_currency=b[3]) for b in meta['branches']]} for code,meta in REGIONS.items()]
