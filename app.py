from flask import Flask, render_template, request
from requests.auth import HTTPBasicAuth
from collections import defaultdict
import requests
import os
from datetime import datetime, timedelta

app = Flask(__name__)

def format_hours_minutes(hours_float):
    hours = int(hours_float)
    minutes = int(round((hours_float - hours) * 60))
    return f"{hours}h {minutes}min"

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        user_email = request.form.get('email', '')  # E-mail do usuário que está sendo consultado
        admin_email = os.getenv("JIRA_ADMIN_EMAIL")  # E-mail da Amanda (administradora)
        api_token = os.getenv("JIRA_API_TOKEN")      # Token da Amanda
        data_inicio_raw = request.form.get('data_inicio', '')
        data_fim_raw = request.form.get('data_fim', '')

        try:
            data_inicio = datetime.strptime(data_inicio_raw, '%Y-%m-%d').strftime('%Y-%m-%d')
            data_fim = datetime.strptime(data_fim_raw, '%Y-%m-%d').strftime('%Y-%m-%d')
        except ValueError:
            return "Erro no formato das datas. Use o seletor de datas corretamente."

        domain = "cooxupe-projetos.atlassian.net"
        base_url = f"https://{domain}/rest/api/3"
        search_url = f"{base_url}/search"

        # JQL atualizado: buscar por atualização recente, sem filtrar por autor
        jql = f'updated >= {data_inicio} AND updated <= {data_fim}'

        query_params = {
            "jql": jql,
            "fields": "summary"
        }

        response = requests.get(search_url, auth=HTTPBasicAuth(admin_email, api_token), params=query_params)
        if response.status_code != 200:
            return f"Erro ao buscar tarefas: {response.status_code} - {response.text}"

        issues = response.json().get("issues", [])
        worklog_summary = defaultdict(lambda: defaultdict(float))

        for issue in issues:
            issue_key = issue["key"]
            summary = issue["fields"]["summary"]
            worklog_url = f"{base_url}/issue/{issue_key}/worklog"

            wl_response = requests.get(worklog_url, auth=HTTPBasicAuth(admin_email, api_token))
            if wl_response.status_code != 200:
                continue

            for wl in wl_response.json().get("worklogs", []):
                if wl["author"].get("emailAddress") != user_email:
                    continue

                started = wl["started"][:10]
                if data_inicio <= started <= data_fim:
                    hours = wl["timeSpentSeconds"] / 3600
                    worklog_summary[started][f"{issue_key} - {summary}"] += hours

        all_dates = sorted(worklog_summary.keys())

        pivot_data = defaultdict(dict)
        for date in all_dates:
            for issue, hrs in worklog_summary[date].items():
                pivot_data[issue][date] = format_hours_minutes(hrs)

        daily_totals = {}
        for date in all_dates:
            total = sum(worklog_summary[date].values())
            daily_totals[date] = format_hours_minutes(total)

        return render_template(
            "dashboard.html",
            email=user_email,
            pivot_data=pivot_data,
            all_dates=all_dates,
            daily_totals=daily_totals
        )

    # GET padrão com datas já preenchidas
    hoje = datetime.today()
    sete_dias_atras = hoje - timedelta(days=7)
    data_inicio = sete_dias_atras.strftime('%Y-%m-%d')
    data_fim = hoje.strftime('%Y-%m-%d')

    return render_template("index.html", data_inicio=data_inicio, data_fim=data_fim)

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%d/%m/%Y'):
    try:
        return datetime.strptime(value, '%Y-%m-%d').strftime(format)
    except:
        return value

if __name__ == '__main__':
    app.run(debug=True)
