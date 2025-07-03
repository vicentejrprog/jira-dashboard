
from flask import Flask, render_template, request
from requests.auth import HTTPBasicAuth
from collections import defaultdict
import requests

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

        data = []
        for date in sorted(worklog_summary.keys()):
            activities = [
                {'issue': issue, 'time': format_hours_minutes(hrs)}
                for issue, hrs in worklog_summary[date].items()
            ]
            total = format_hours_minutes(sum(worklog_summary[date].values()))
            data.append({'date': date, 'activities': activities, 'total': total})

        return render_template("dashboard.html", email=email, data=data)


    return render_template("index.html")
if __name__ == '__main__':
    app.run(debug=True)