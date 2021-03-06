    from locust import HttpLocust, TaskSet, task
    import re
    import random
    import queue

    class WebsiteTasks(TaskSet):
        # 用户下单的流程
        @task(1)
        def jiayoukaRecharge(self):
            try:
                data = self.locust.user_data_queue.get()
                self.locust.user_data_queue.put_nowait(data)
            except queue.Empty:
                print('queue is empty')
                exit(0)
            # 随机进行中石油or中石化充值
            r = random.randint(1, 2)
            if r == 1:
                print('中石化充值流程')
                category = '中石化'
                # 默认值，防止取不到回传数据，影响接下来的接口
                cardId = '1000113100010404771'
                productId = '20181505193523'
            else:
                print('中石油充值流程')
                category = '中石油'
                # 默认值，防止取不到回传数据，影响接下来的接口
                cardId = '9030400001313871'
                productId = '1503233311'
            try:
                # main_info
                with self.client.get(
                        "/api/common/v1/main/info?",
                        catch_response=True,
                        timeout=3
                )as response:
                    if response.json()['code'] != 0:
                        response.failure(response.json())
                # 绑定用户
                with self.client.get(
                        "/api/bindUser/v1?customerUserPhone={}&customerUserId={}&categoryCode=jiayouka".format(data['userId'], data['phone']),
                        catch_response=True,
                        name="/api/bindUser/v1?",
                        timeout=3
                )as response:
                    if response.json()['code'] != 0:
                        response.failure(response.json())
                # 无油卡数据则新建加油卡
                with self.client.get(
                        "/api/jiayouka/v1/{}/cards/{}?".format(r, data['userId']),
                        catch_response=True,
                        name="/jiayouka/v1/:categoryId/cards/:customerUserId",
                        timeout=3
                )as response:
                    if response.json()["code"] != 0:
                        response.failure("加油卡列表接口，code不为0:{}".format(response.json()))
                    else:
                        if len(response.json()['data']) < 1:
                            self.client.post(
                                "/api/jiayouka/v1/cards", {
                                    "id": "",
                                    "cardId": cardId,
                                    "userName": "",
                                    "credentialNum": "",
                                    "phone": data['phone'],
                                    "showBasisNameList": ["autohome", "pingan-one", "localhost"],
                                    "isShowBasis": False,
                                    "customerUserId": data['userId'],
                                    "credentialType": "身份证",
                                    "categoryId": "{}".format(r)
                                },
                                catch_response=True,
                                name="/jiayouka/v1/cards",
                                timeout=3
                            )
                # 获取可用服务商
                with self.client.get(
                        "/api/jiayouka/v1/list",
                        catch_response=True,
                        name="/api/jiayouka/v1/list",
                        timeout=3
                )as response:
                    if re.search(category, response.text) is None:
                        response.failure("未回传{}" .format(category))
                # 获取用户加油卡列表
                with self.client.get(
                    "/api/jiayouka/v1/{}/cards/{}?".format(r, data['userId']),
                        catch_response=True,
                        name="/jiayouka/v1/:categoryId/cards/:customerUserId",
                        timeout=3
                )as response:
                    if len(response.json()["data"]) > 0:
                        cardId = response.json()["data"][0]['cardId']
                    else:
                        response.failure("未获取到用户{}加油卡数据".format(category))

                # 获取可充值套餐
                with self.client.get(
                    "/api/jiayouka/v1/{}/payments?".format(r),
                        catch_response=True,
                        name="/jiayouka/v1/:categoryId/payments",
                        timeout=3
                )as response:
                    if response.json()['code'] != 0 or len(response.json()['data']) < 1:
                        response.failure("无可用套餐:{}".format(response.json()))
                    else:
                        productId = response.json()['data'][0]['productId']
                # 下单
                with self.client.post(
                        "/api/jiayouka/v1/order", {
                            "productId": productId,
                            "customerUserId": data['userId'],
                            "cardId": cardId,
                            "categoryId": "{}".format(r),
                            "userPhone": data['phone'],
                            "phone": "18810528271",
                            "userName": "测试",
                            "couponId": "",
                            "activityId": ""
                        },
                        catch_response=True,
                        name="/jiayouka/v1/order",
                        timeout=3
                )as response:
                    text = response.text
                    if re.search('"id":"(.*)","name"', text) is not None:
                        id = re.search('"id":"(.*)","name"', text).group(1)
                        # 收银台获取lite数据
                        with self.client.get("/api/order/v1/lite/{0}?id={0}&subId=&orderType=jiayouka".format(id),
                                             catch_response=True,
                                             name='/order/v1/lite/:id?id=:id&subId=&orderType=jiayouka',
                                             timeout=3
                                             ) as response:
                            if response.json()['code'] != 0:
                                response.failure("订单详情{}，response:{}".format(id, response.json()))
                        # TODO 暂缺模拟支付。如果host和其他接口不一致需要先修改self.host 然后 再改回来。
                        # 支付成功后获取订单详情
                        with self.client.get("/api/order/v1/jiayouka/{}/info?".format(id),
                                             catch_response=True,
                                             name='/order/v1/jiayouka/:id/info?',
                                             timeout=3
                                             ) as response:
                            # TODO 加了支付后可以考虑加个判断是否回传的status已经不是已下单or待支付
                            if response.json()['code'] != 0:
                                response.failure("订单详情{}，response:{}".format(id, response.json()))
                    else:
                        response.failure("下单接口，没有获取到生成的订单id:{}".format(text))

            except Exception as e:
                response.failure("errMessage:{},response:{}".format(e, response.text))

        @task(1)
        def getOrderList(self):
            # 查看订单列表
            data = self.locust.user_data_queue.get()
            self.locust.user_data_queue.put_nowait(data)
            try:
                with self.client.get(
                    "/api/order/v1/{}/orders?orderType=coffee&pageSize=10&pageIndex=1".format(data['userId']),
                        catch_response=True,
                        name='/order/v1/:userId/orders?orderType=coffee&pageSize=10&pageIndex=1',
                        timeout=3
                )as response:
                    if response.json()['code'] != 0:
                        response.failure(response.json())
            except Exception as e:
                response.failure("errMessage:{},response:{}".format(e, response.text))

    class WebsiteUser(HttpLocust):
        task_set = WebsiteTasks
        # TODO host需要切换为内网ip
        # host = 'https://dev-me.otosaas.com'
        # 生成用户数据，开发说用同样的数据他们那边会读缓存，性能数据会不准确
        user_data_queue = queue.Queue()
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
