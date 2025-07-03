from flask import Flask, render_template, request
from requests.auth import HTTPBasicAuth
from collections import defaultdict
import requests
from datetime import datetime
app = Flask(__name__)


def format_hours_minutes(hours_float):
    hours = int(hours_float)
    minutes = int(round((hours_float - hours) * 60))
    return f"{hours}h {minutes}min"

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        email = request.form['email']
        api_token = request.form['api']

        domain = "cooxupe-projetos.atlassian.net"
        base_url = f"https://{domain}/rest/api/3"
        search_url = f"{base_url}/search"

        query_params = {
            "jql": "worklogAuthor = currentUser() AND worklogDate >= startOfMonth()",
            "fields": "summary"
        }

        response = requests.get(search_url, auth=HTTPBasicAuth(email, api_token), params=query_params)
        if response.status_code != 200:
            return f"Erro ao buscar tarefas: {response.status_code} - {response.text}"

        issues = response.json().get("issues", [])
        worklog_summary = defaultdict(lambda: defaultdict(float))

        for issue in issues:
            issue_key = issue["key"]
            summary = issue["fields"]["summary"]
            worklog_url = f"{base_url}/issue/{issue_key}/worklog"

            wl_response = requests.get(worklog_url, auth=HTTPBasicAuth(email, api_token))
            if wl_response.status_code != 200:
                continue

            for wl in wl_response.json().get("worklogs", []):
                if wl["author"].get("emailAddress") != email:
                    continue

                started = wl["started"][:10]
                hours = wl["timeSpentSeconds"] / 3600
                worklog_summary[started][f"{issue_key} - {summary}"] += hours

        # Coletar todas as datas
        all_dates = sorted(worklog_summary.keys())

        # Reorganiza os dados por atividade → data → horas
        pivot_data = defaultdict(dict)
        for date in all_dates:
            for issue, hrs in worklog_summary[date].items():
                pivot_data[issue][date] = format_hours_minutes(hrs)

        return render_template("dashboard.html", email=email, pivot_data=pivot_data, all_dates=all_dates)

    return render_template("index.html")


@app.template_filter('datetimeformat')
def datetimeformat(value, format='%d/%m/%Y'):
    try:
        return datetime.strptime(value, '%Y-%m-%d').strftime(format)
    except:
        return value

if __name__ == '__main__':
    app.run(debug=True)
