"""Copyright 2017 Istio Authors. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import logging
import re

from airflow import DAG
from airflow.models import Variable
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator

import environment_config
import istio_common_dag


def MonthlyPipeline():
  MONTHLY_RELEASE_TRIGGER = '15 17 * * 4#3'

  def MonthlyGenerateTestArgs(**kwargs):
    release_params = dict(
      DOCKER_HUB='istio',
      GCR_RELEASE_DEST='istio-io',
      GCS_GITHUB_PATH='istio-secrets/github.txt.enc',
      GCS_MONTHLY_RELEASE_PATH='istio-release/releases/{version}',
      RELEASE_PROJECT_ID='istio-io',
      VERIFY_CONSISTENCY='true')

    """Loads the configuration that will be used for this Iteration."""
    conf = kwargs['dag_run'].conf
    if conf is None:
      conf = dict()

    # If version is overriden then we should use it otherwise we use it's
    # default or monthly value.
    version = conf.get('VERSION') or istio_common_dag.GetVariableOrDefault('monthly-version', None)
    if not version or version == 'INVALID':
      raise ValueError('version needs to be provided')
    Variable.set('monthly-version', 'INVALID')

    GCS_MONTHLY_STAGE_PATH='prerelease/{version}'
    gcs_path = GCS_MONTHLY_STAGE_PATH.format(version=version)

    branch = conf.get('BRANCH') or istio_common_dag.GetVariableOrDefault('monthly-branch', None)
    if not branch or branch == 'INVALID':
      raise ValueError('branch needs to be provided')
    Variable.set('monthly-branch', 'INVALID')
    mfest_commit = conf.get('MFEST_COMMIT') or branch

    default_conf = environment_config.get_default_config(
        branch=branch,
        gcs_path=gcs_path,
        mfest_commit=mfest_commit,
        verify_consistency=release_params['VERIFY_CONSISTENCY'],
        version=version)

    config_settings = dict()
    for name in default_conf.iterkeys():
      config_settings[name] = conf.get(name) or default_conf[name]

    monthly_conf = dict(release_params)
    monthly_conf['GCS_MONTHLY_RELEASE_PATH'] = release_params['GCS_MONTHLY_RELEASE_PATH'].format(
		version=config_settings['VERSION'])
    for name in release_params.iterkeys():
      config_settings[name] = conf.get(name) or monthly_conf[name]
    config_settings['PIPELINE_TYPE'] = 'monthly'
    return config_settings

  dag, tasks = istio_common_dag.MakeCommonDag(
    MonthlyGenerateTestArgs,
    'istio_monthly_dag',
    schedule_interval=MONTHLY_RELEASE_TRIGGER)

  release_push_github_docker_template = """
{% set m_commit = task_instance.xcom_pull(task_ids='get_git_commit') %}
{% set settings = task_instance.xcom_pull(task_ids='generate_workflow_args') %}
gsutil cp gs://{{ settings.GCS_RELEASE_TOOLS_PATH }}/data/release/*.json .
gsutil cp gs://{{ settings.GCS_RELEASE_TOOLS_PATH }}/data/release/*.sh .
chmod u+x *
./start_gcb_publish.sh \
-p "{{ settings.RELEASE_PROJECT_ID }}" -a "{{ settings.SVC_ACCT }}"  \
-v "{{ settings.VERSION }}" -s "{{ settings.GCS_FULL_STAGING_PATH }}" \
-b "{{ settings.GCS_MONTHLY_RELEASE_PATH }}" -r "{{ settings.GCR_RELEASE_DEST }}" \
-g "{{ settings.GCS_GITHUB_PATH }}" -u "{{ settings.MFEST_URL }}" \
-t "{{ m_commit }}" -m "{{ settings.MFEST_FILE }}" \
-h "{{ settings.GITHUB_ORG }}" -i "{{ settings.GITHUB_REPO }}" \
-d "{{ settings.DOCKER_HUB}}" -w
"""

  github_and_docker_release = BashOperator(
    task_id='github_and_docker_release',
    bash_command=release_push_github_docker_template,
    dag=dag)
  tasks['github_and_docker_release'] = github_and_docker_release

  release_tag_github_template = """
{% set m_commit = task_instance.xcom_pull(task_ids='get_git_commit') %}
{% set settings = task_instance.xcom_pull(task_ids='generate_workflow_args') %}
gsutil cp gs://{{ settings.GCS_RELEASE_TOOLS_PATH }}/data/release/*.json .
gsutil cp gs://{{ settings.GCS_RELEASE_TOOLS_PATH }}/data/release/*.sh .
chmod u+x *
./start_gcb_tag.sh \
-p "{{ settings.RELEASE_PROJECT_ID }}" \
-h "{{ settings.GITHUB_ORG }}" -a "{{ settings.SVC_ACCT }}"  \
-v "{{ settings.VERSION }}"   -e "istio_releaser_bot@example.com" \
-n "IstioReleaserBot" -s "{{ settings.GCS_FULL_STAGING_PATH }}" \
-g "{{ settings.GCS_GITHUB_PATH }}" -u "{{ settings.MFEST_URL }}" \
-t "{{ m_commit }}" -m "{{ settings.MFEST_FILE }}" -w
"""

  github_tag_repos = BashOperator(
    task_id='github_tag_repos',
    bash_command=release_tag_github_template,
    dag=dag)
  tasks['github_tag_repos'] = github_tag_repos


  def ReportMonthlySuccessful(task_instance, **kwargs):
    del kwargs

  mark_monthly_complete = PythonOperator(
    task_id='mark_monthly_complete',
    python_callable=ReportMonthlySuccessful,
    provide_context=True,
    dag=dag,
  )
  tasks['mark_monthly_complete'] = mark_monthly_complete

# tasks['generate_workflow_args']
  tasks['get_git_commit'                 ].set_upstream(tasks['generate_workflow_args'])
  tasks['run_cloud_builder'              ].set_upstream(tasks['get_git_commit'])
  tasks['run_release_qualification_tests'].set_upstream(tasks['run_cloud_builder'])
  tasks['copy_files_for_release'         ].set_upstream(tasks['run_release_qualification_tests'])
  tasks['github_and_docker_release'      ].set_upstream(tasks['copy_files_for_release'])
  tasks['github_tag_repos'               ].set_upstream(tasks['github_and_docker_release'])
  tasks['mark_monthly_complete'          ].set_upstream(tasks['github_tag_repos'])

  return dag




dagMonthly = MonthlyPipeline()
dagMonthly