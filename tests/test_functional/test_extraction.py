import run
import os
import time
import subprocess
import sys
from lib.test_base import TestGeneric
from settings import PROJ_HOME, CONSTANTS
from lib import CheckIfExtract as check_if_extract


class TestExtractWorker(TestGeneric):

    def setUp(self):
        self.expected_folders = []
        # Start the pipeline
        try:
            self.supervisor_ADS_full_text(action='start', pipeline='Group')
        except:
            print "WARNING: COULD NOT START TESTING PIPELINE"
            pass
        # try:
        #     self.supervisor_ADS_full_text(action='start', pipeline='Java')
        # except:
        #     print "WARNING: COULD NOT START JAVA PIPELINE"
        #     pass
        time.sleep(3)

    def tearDown(self):
        self.connect_publisher()
        self.purge_all_queues()
        self.clean_up_path(self.expected_folders)

        # Stop the pipeline
        try:
            self.supervisor_ADS_full_text(action='stop', pipeline='Group')
        except:
            print "WARNING: COULD NOT STOP TESTING PIPELINE"
            pass
        # try:
        #     self.supervisor_ADS_full_text(action='stop', pipeline='Python')
        # except:
        #     print "WARNING: COULD NOT STOP PYTHON PIPELINE"
        #     pass

    def supervisor_ADS_full_text(self, action, pipeline):

        pipeline_d = {'Python': 'ADSfulltext',
                      'Java': 'ADSfulltextPDFLIVE',
                      'Group': 'GroupADSfulltextTEST:*'}

        accepted_actions = ['stop', 'start']
        if action not in accepted_actions:
            print 'You can only use: %s' % accepted_actions
            return

        process = subprocess.Popen(['supervisorctl', '-c', '/etc/supervisord.conf', action, pipeline_d[pipeline]],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        output, error = process.communicate()

        if action not in output:
            raise Exception('ADSfull text could not be started correctly, exiting', output, error)

    def test_functionality_of_the_system_on_non_existent_files(self):

        full_text_links = 'tests/test_functional/stub_data/fulltext_functional_tests.links'
        # Obtain the parameters to publish to the queue
        # Expect that the records are split into the correct number of
        # packet sizes
        run.run(full_text_links=os.path.join(PROJ_HOME, full_text_links),
                 packet_size=10)

        time.sleep(10)

        self.expected_folders = self.calculate_expected_folders(full_text_links)

        for expected_f in self.expected_folders:
            self.assertTrue(os.path.exists(expected_f), 'Could not find: %s' % expected_f)
            self.assertTrue(os.path.exists(os.path.join(expected_f, 'meta.json')), 'Could not find: %s' % os.path.join(expected_f, 'meta.json'))
            self.assertTrue(os.path.exists(os.path.join(expected_f, 'fulltext.txt')), 'Could not find: %s' % os.path.join(expected_f, 'fulltext.txt'))


if __name__ == "__main__":
    unittest.main()