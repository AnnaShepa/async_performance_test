The script tests performance using different methods of import through REST API in Magento 2. Script sends different amount of items to Sync, Async and Bulk endpoints. Different types of items and requests can be added in Entities class. Currently it includes requests to create next items:
 - Simple product
 - Configurable product
 - Customer
 
Script accept 3 arguments on run:
- host
- tocken to send API calls
- max_batch_size (several runs will be done with items amount from 1 to max_batch_size with step 10, e.g. [1, 10, 20])

To run the Script you will need to install requests and matplotlib libraries.

More information and results are described here: https://community.magento.com/t5/Magento-DevBlog/Asynchronous-Bulk-API-Performance-Test/ba-p/414878
