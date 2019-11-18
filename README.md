The script was created to test performance using different methods of import through REST API in Magento. Script sends different amount of items to Sync, Async and Bulk endpoints. Different types of items and requests can be added im Entities class. Currently it includes simple product creation and customer creation requests. 
Script accept 3 arguments on run:
- host
- tocken to send API calls
- max_batch_size (several runs will be done with items amount from 1 to max_batch_size with step 10)
