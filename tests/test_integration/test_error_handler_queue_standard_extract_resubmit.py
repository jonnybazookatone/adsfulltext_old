from lib.test_base import *


class TestExtractWorker(TestGeneric):

    def tearDown(self):
        self.clean_up_path(self.expected_paths)

        super(TestExtractWorker, self).tearDown()


    def setUp(self):

        super(TestExtractWorker, self).setUp()
        self.test_publish = os.path.join(PROJ_HOME, 'tests/test_integration/stub_data/fulltext_error_handling_standard_extract_resubmitted.links')
        self.expected_paths = self.calculate_expected_folders(self.test_publish)



    def test_extraction_of_non_extracted(self):

        # user loads the list of full text files and publishes them to the first queue
        records = read_links_from_file(self.test_publish)

        self.helper_get_details(self.test_publish)
        self.assertEqual(len(records.bibcode), self.nor,
                         "The number of records should match the number of lines. It does not: %d [%d]"
                         % (len(records.bibcode),self.nor))

        # The pipeline converts the input into a payload expected by the workers
        records.make_payload()
        self.assertTrue(len(records.payload)>0)

        # External worker publishes the payload created before to the RabbitMQ queue
        # for the workers to start consuming
        ret = publish(self.publish_worker, records.payload, exchange='FulltextExtractionExchange',
                      routing_key='CheckIfExtractRoute')
        self.assertTrue(ret)
        time.sleep(10)

        # Worker receives packet of information and checks to see if it needs to be updated
        print('starting check worker...')
        self.check_worker.run()

        # We pause to simulate the asynchronous running of the workers. This is not needed when the workers
        # are listening continuously.
        print('sleeping')
        time.sleep(10)
        print('continuing')
        # Check to see if the correct number of updates got published to the next queue
        ## Re-declare the queue with passive flag
        standard_queue = self.check_worker.channel.queue_declare(
            queue="StandardFileExtractorQueue",
            passive=True
            )

        pdf_queue = self.check_worker.channel.queue_declare(
            queue="PDFFileExtractorQueue",
            passive=True
            )

        self.assertTrue(standard_queue.method.message_count,
                        "Standard queue should have at least 1 message, but it has: %d" %
                        (standard_queue.method.message_count))

        # Double check with the worker output
        pdf_res = json.loads(self.check_worker.results["PDF"])
        standard_res = json.loads(self.check_worker.results["Standard"])

        extract_type = 'NOT_EXTRACTED_BEFORE'
        for res in standard_res:
            self.assertEqual(res[CONSTANTS['UPDATE']], extract_type,
                             'This should be %s, but is in fact: %s' % (extract_type, res[CONSTANTS['UPDATE']]))

        # Now the next worker collects the list of files that need to be extracted. The Standard
        # Extractor should extract the content of the given payload and so the number of outputs
        # should match the number before. Given we don't expect any errors here!
        print('starting extractor worker...')
        self.standard_worker.run()
        print('sleeping')
        time.sleep(10)
        print('continuing')

        # There should be no errors at this stage
        queue_error = self.check_worker.channel.queue_declare(
            queue="ErrorHandlerQueue",
            passive=True
            )
        self.assertTrue(queue_error.method.message_count == 1,
                        "Should be 1, but it is: %d" % queue_error.method.message_count)

        print('starting error handler')
        self.error_worker.run()
        time.sleep(10)
        queue_error = self.check_worker.channel.queue_declare(
            queue="ErrorHandlerQueue",
            passive=True
            )
        self.assertTrue(queue_error.method.message_count == 0,
                        "Should be 0, but it is: %d" % queue_error.method.message_count)

        # The error handler should resubmit each individual payload back to the queue that failed
        standard_queue = self.check_worker.channel.queue_declare(
            queue="WriteMetaFileQueue",
            passive=True
            )
        self.assertTrue(standard_queue.method.message_count,
                        "WriteMetaFileQueue should have at least 1 message, but it has: %d" %
                        standard_queue.method.message_count)

        # StandardExtractor should then work its magic on the single resubmission
        print('starting meta writer')
        self.meta_writer.run()

        for path in [self.expected_paths[1]]:
            self.assertTrue(os.path.exists(path), "Meta path not created: %s" % path)


if __name__ == "__main__":
    unittest.main()