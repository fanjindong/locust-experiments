    from locust import HttpLocust, TaskSet, task
    import re
    import random
    import queue
    import traceback

    class WebsiteTasks(TaskSet):

        @task(1)
        def fetchOrderMessage(self):

            try:
                data = self.locust.order_data_queue.get()
            except queue.Empty:
                print('order_data_queue is empty')
                exit(0)

            try:
                response = None
                response = self.client.get('/sm/order/fetch/{}'.format(data['orderId']),
                                           name='/sm/order/fetch/:orderId')
                resp_json = response.json()

                if resp_json['code'] != 0:
                    response.failure(resp_json)

                self.locust.order_data_queue.put_nowait(data)

            except:
                response.failure("errMessage:{}, response.statusCode:{} ,response:{}".format(
                    traceback.format_exc(),
                    response.status_code,
                    response.text if response else None
                ))

        @task(1)
        def fetchOrderList(self):
            try:
                data = self.locust.user_data_queue.get()
            except queue.Empty:
                print('user_data_queue is empty')
                exit(0)

            try:
                response = None
                response = self.client.post('/sm/order/fetch_lite_list', json={'userId': data['userId'], 'appCode': 'blm'})
                resp_json = response.json()

                if resp_json['code'] != 0:
                    response.failure(resp_json)

                for item in resp_json['data']:
                    self.locust.order_data_queue.put_nowait({"orderId": item['id']})

                self.locust.user_data_queue.put_nowait(data)

            except:
                response.failure("errMessage:{}, response.statusCode:{} ,response:{}".format(
                    traceback.format_exc(),
                    response.status_code,
                    response.text if response else None
                ))

    class WebsiteUser(HttpLocust):
        task_set = WebsiteTasks
        # TODO host需要切换为内网ip
        # host = 'https://dev-me.otosaas.com'
        # 生成用户数据，开发说用同样的数据他们那边会读缓存，性能数据会不准确
        user_data_queue = queue.Queue()
        order_data_queue = queue.Queue()
        # 数值待定。。
        for index in range(1000):
            data = {
                "userId": "test%04d" % index,
                "phone": "186%08d" % index
            }
            user_data_queue.put_nowait(data)

        min_wait = 10
        max_wait = 300

        # stop_timeout = None
        """Number of seconds after which the Locust will die. If None it won't timeout."""
