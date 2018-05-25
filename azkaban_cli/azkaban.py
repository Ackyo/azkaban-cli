from __future__ import absolute_import
from shutil import make_archive
from urllib3.exceptions import InsecureRequestWarning
import azkaban_cli.api as api
import logging
import os
import requests
import urllib3

class Azkaban(object):
    def __init__(self):
        # Session ignoring SSL verify requests
        session = requests.Session()
        session.verify = False
        urllib3.disable_warnings(InsecureRequestWarning)

        self.__session = session

        self.__host = None
        self.__session_id = None

    def __validate_host(self, host):
        valid_host = host

        while valid_host.endswith(u'/'):
            valid_host = valid_host[:-1]

        return valid_host

    def get_logged_session(self):
        """Method for return the host and session id of the logged session saved on the class

        :return: A dictionary containing host and session_id as keys
        :rtype: dict
        """

        logged_session = {
            u'host': self.__host,
            u'session_id': self.__session_id
        }

        return logged_session

    def set_logged_session(self, host, session_id):
        """Method for set host and session_id, attributes of the class

        :param host: Azkaban hostname
        :type host: str
        :param session_id: session.id received from a login request
        :type session_id: str
        """

        self.__host = host
        self.__session_id = session_id

    def logout(self):
        """Logout command, intended to clear the host and session_id attributes from the class"""

        self.set_logged_session(None, None)

    def login(self, host, user, password):
        """Login command, intended to make the request to Azkaban and treat the response properly

        This method validate the host, make the request to Azkaban, and avaliate the response. If host, user or
        password is wrong or could not connect to host, it returns false and do not change the host and session_id
        attribute from the class. If everything is fine, saves the new session_id and corresponding host as attributes
        in the class and returns True

        :param str host: Azkaban hostname
        :param str user: Username to login
        :param str password: Password from user
        :return: True if everything is fine, False if something goes wrong
        :rtype: bool
        """

        valid_host = self.__validate_host(host)

        try:
            response_json = api.login_request(self.__session, valid_host, user, password).json()
        except requests.exceptions.ConnectionError:
            logging.error("Could not connect to host")
            return False

        if u'error' in response_json.keys():
            error_msg = response_json[u'error']
            logging.error(error_msg)
            return False

        self.set_logged_session(valid_host, response_json['session.id'])

        logging.info('Logged as %s' % (user))

        return True

    def upload(self, path, project=None, zip_name=None):
        """Upload command, intended to make the request to Azkaban and treat the response properly

        This method receives a path to a directory that contains all the files that should be in the Azkaban project,
        zip this path (as Azkaban expects it zipped), make the upload request to Azkaban, deletes the zip that was
        created and avaliate the response.

        If project name is not passed as argument, it will be assumed that the project name is the basename of the path
        passed. If zip name is not passed as argument, the project name will be used for the zip.

        If project or path is wrong or if there is no session_id, it returns false. If everything is fine, returns True.

        :param path: path to be zipped and uploaded
        :type path: str
        :param project: Project name on Azkaban
        :param project: str, optional
        :param zip_name: Zip name that will be created and uploaded
        :param zip_name: str, optional
        :return: True if everything is fine, False if something goes wrong
        :rtype: bool
        """

        if not self.__session_id:
            logging.error(u'You are not logged')
            return False

        if not project:
            # define project name as basename
            project = os.path.basename(os.path.abspath(path))

        if not zip_name:
            # define zip name as project name
            zip_name = project

        try:
            zip_path = make_archive(zip_name, 'zip', path)
        except FileNotFoundError as e:
            logging.error(str(e))
            return False

        response_json = api.upload_request(self.__session ,self.__host, self.__session_id, project, zip_path).json()

        os.remove(zip_path)

        if u'error' in response_json.keys():
            error_msg = response_json[u'error']
            logging.error(error_msg)
            return False
        else:
            logging.info('Project %s updated to version %s' % (project, response_json[u'version']))
            return True

    def schedule(self, project, flow, cron):
        """Schedule command, intended to make the request to Azkaban and treat the response properly.

        This method receives the project, the flow and the cron expression in quartz format, make the schedule request
        to schedule the flow with the cron specified and avaliate the response.

        If project, flow or cron is wrong or if there is no session_id, it returns false. If everything is fine, returns
        True.

        :param project: Project name on Azkaban
        :type project: str
        :param flow: Flow name on Azkaban
        :type flow: str
        :param cron: Cron expression, in quartz format
        :type cron: str
        :return: True if everything is fine, False if something goes wrong
        :rtype: bool
        """

        if not self.__session_id:
            logging.error(u'You are not logged')
            return False

        response_json = api.schedule_request(self.__session, self.__host, self.__session_id, project, flow, cron).json()

        if u'error' in response_json.keys():
            error_msg = response_json[u'error']
            logging.error(error_msg)
            return False
        else:
            if response_json[u'status'] == u'error':
                logging.error(response_json[u'message'])
                return False
            else:
                logging.info(response_json[u'message'])
                logging.info('scheduleId: %s' % (response_json[u'scheduleId']))
                return True

    def execute(self, project, flow):
        """Execute command, intended to make the request to Azkaban and treat the response properly.

        This method receives the project and the flow, make the execute request to execute the flow and avaliate the
        response.

        If project or flow is wrong or if there is no session_id, it returns false. If everything is fine, returns True.

        :param project: Project name on Azkaban
        :type project: str
        :param flow: Flow name on Azkaban
        :type flow: str
        :return: True if everything is fine, False if something goes wrong
        :rtype: bool
        """

        if not self.__session_id:
            logging.error(u'You are not logged')
            return False

        response_json = api.execute_request(
            self.__session,
            self.__host,
            self.__session_id,
            project,
            flow,
        ).json()

        if u'error' in response_json.keys():
            error_msg = response_json[u'error']
            logging.error(error_msg)
            return False
        else:
            logging.info('%s' % (response_json[u'message']))
            return True
