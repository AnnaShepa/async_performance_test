from abc import ABC, abstractmethod
from datetime import datetime
import random


class Batch():
    def __init__(self, size, entity):
        self._start_timestamp = int(datetime.timestamp(datetime.utcnow()))
        self._size = size
        self._entity = entity
        self.elapsed_sum = 0
        self.bulk_uuids = []

    @property
    def start_timestamp(self):
        return self._start_timestamp

    @property
    def size(self):
        return self._size

    @property
    def entity(self):
        return self._entity


class Entity(ABC):
    name: str
    create_endpoint_key: str
    search_endpoint_key: str
    search_by_field: str

    @abstractmethod
    def create_request_body(self, item_id):
        pass


class SimpleProduct(Entity):
    name = 'Simple Product'
    create_endpoint_key = 'products'
    search_endpoint_key = 'products'
    search_by_field = 'sku'

    def create_request_body(self, item_id):
        return {
            "product": {
                "sku": item_id,
                "name": item_id,
                "attribute_set_id": 4,
                "price": "100",
                "status": 1,
                "visibility": 4,
                "type_id": "simple",
                "extension_attributes": {
                    "stock_item": {
                        "manage_stock": 1,
                        "is_in_stock": 1,
                        "qty": "10"
                    }
                }
            }
        }


class ConfigurableProduct(Entity):
    name = 'Configurable Product'
    create_endpoint_key = 'products'
    search_endpoint_key = 'products'
    search_by_field = 'sku'

    def create_request_body(self, item_id):
        return {
            "product": {
                "sku": item_id,
                "name": item_id,
                "attribute_set_id": 4,
                "price": "0",
                "status": 1,
                "visibility": 4,
                "type_id": "configurable",
                "weight": 0.5,
                "extension_attributes": {
                    "category_links": [
                        {
                            "position": 0,
                            "category_id": "3"
                        }
                    ],
                    "configurable_product_options": [
                        {
                            "attribute_id": "93",
                            "label": "Color",
                            "position": 0,
                            "is_use_default": "false",
                            "values": [
                                {
                                    "value_index": 14
                                },
                                {
                                    "value_index": 43
                                },
                                {
                                    "value_index": 47
                                }
                            ]
                        }
                    ]
                }
            }
        }


class Customer(Entity):
    name = 'Customer'
    create_endpoint_key = 'customers'
    search_endpoint_key = 'customers/search'
    search_by_field = 'email'

    def create_request_body(self, item_id):
        return {
            "customer": {
                "email": item_id + "@mailinator.com",
                "firstname": "Test",
                "lastname": "Auto"
            },
            "password": "Strong-Password"
        }


class Price(Entity):
    name = 'Price'
    create_endpoint_key = 'products/base-prices'
    search_endpoint_key = 'products'
    search_by_field = 'sku'
    price = random.randint(1, 1500)

    def create_request_body(self, item_id):
        return {
            "prices": [
                {
                    "price": self.price,
                    "store_id": 0,
                    "sku": item_id
                }
            ]
        }
