import unittest
from src.core.network import NetworkManager

class TestNetworkManager(unittest.TestCase):
    def setUp(self):
        self.network_manager = NetworkManager()

    def test_connect(self):
        result = self.network_manager.connect('localhost', 12345)
        self.assertTrue(result)

    def test_send_message(self):
        self.network_manager.connect('localhost', 12345)
        result = self.network_manager.send_message('Hello, World!')
        self.assertTrue(result)

    def test_receive_message(self):
        self.network_manager.connect('localhost', 12345)
        self.network_manager.send_message('Hello, World!')
        message = self.network_manager.receive_message()
        self.assertEqual(message, 'Hello, World!')

    def tearDown(self):
        self.network_manager.disconnect()

if __name__ == '__main__':
    unittest.main()