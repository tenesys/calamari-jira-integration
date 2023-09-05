# Calamari - Jira integration
This integration is syncing absences and timesheets between Jira and Calamari.

## How to build and run
```
pip3 install -r requirements.txt -t build
cd build
zip -r ../build.zip .
```
Then upload ZIP to Lambda function.

## Settings
Settings by default are taken from environmental variables. There is also support for the AWS System Manager Parameter Store. You can switch the source of the settings by changing env `SETTINGS_STORE` to `ssm_parameters`.

List of available settings:
| Name                                 | Description                                                                                 | Default value |
| ------------------------------------ | ------------------------------------------------------------------------------------------- | ------------- |
| `debug`                              | Whether debug logging is enabled                                                            | `0`           |
| `calamari_api_url`                   | Calamari API URL, e.g. `example.calamari.io`                                                |               |
| `calamari_api_token`                 | Calamari API token                                                                          |               |
| `calamari_absence_ignored_employees` | List of ignored employees during absence sync, e.g. `j.doe1@example.com,j.doe2@example.com` |               |
| `calamari_absence_ignored_types`     | List of ignored types during absence sync                                                   |               |
| `calamari_timesheet_contract_types`  | List of contract types for timesheet sync                                                   |               |
| `jira_api_url`                       | Jira API URL, e.g. `example.atlassian.net`                                                  |               |
| `jira_api_user`                      | Jira API username                                                                           |               |
| `jira_api_token`                     | Jira API token                                                                              |               |
| `jira_absence_issue`                 | Jira issue key for absence worklogs, e.g. `ABC-123`                                         |               |
| `jira_absence_worklog_description`   | Description for absence worklogs                                                            | `Absence`     |
| `tempo_api_token`                    | Tempo API token                                                                             |               |
| `notification_emails`                | List of emails to send notifications, e.g. `j.doe1@example.com,j.doe2@example.com`          |               |
| `notification_from_email`            | `From` email address                                                                        |               |


## Absence sync (Calamari -> Jira)
Sync takes approved absences from Calamari and reports them as worklogs in Tempo. Worklogs are created on the issue key taken from the `jira_absence_issue` setting. During the sync, all absences are taken into account except for employees listed in `calamari_absence_ignored_employees` and absence types defined in `calamari_absence_ignored_types`.

After each sync notification is sent with conflicts (e.g. when an employee reports absence in Jira but not in Calamari).

## Timesheet sync (Jira -> Calamari)
During the sync, Tempo worklogs are summed up and reported to the Calamari timesheet. It takes place for employees with contract types listed in `calamari_timesheet_contract_types`. Worklogs from issue defined in `jira_absence_issue` are ignored.
