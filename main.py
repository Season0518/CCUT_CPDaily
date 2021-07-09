import yaml
import base64
import json
import re
import uuid
import re
import json
import requests
from pyDes import PAD_PKCS5, des, CBC

from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class iapLogin:
    def __init__(self, username, password, login_url, host, session):
        self.username = username
        self.password = password
        self.login_url = login_url
        self.host = host
        self.session = session
        self.ltInfo = None
        self.count = 0

    # 判断是否需要验证码
    def getNeedCaptchaUrl(self):
        data = self.session.post(f'{self.host}iap/checkNeedCaptcha?username={self.username}', data=json.dumps({}),
                                 verify=False).json()
        return data['needCaptcha']

    def login(self):
        params = {}
        self.ltInfo = self.session.post(f'{self.host}iap/security/lt', data=json.dumps({})).json()
        params['lt'] = self.ltInfo['result']['_lt']
        params['rememberMe'] = 'false'
        params['dllt'] = ''
        params['mobile'] = ''
        params['username'] = self.username
        params['password'] = self.password
        params['captcha'] = ''
        data = self.session.post(f'{ self.host }iap/doLogin', params=params, verify=False, allow_redirects=False)
        if data.status_code == 302:
            data = self.session.post(data.headers['Location'], verify=False)
            return self.session.cookies
        else:
            data = data.json()
            self.count += 1
            if data['resultCode'] == 'CAPTCHA_NOTMATCH':
                if self.count < 10:
                    self.login()
                else:
                    raise Exception('验证码错误超过10次，请检查')
            elif data['resultCode'] == 'FAIL_UPNOTMATCH':
                raise Exception('用户名密码不匹配，请检查')

class TodayLoginService:
    # 初始化本地登录类
    def __init__(self, userInfo):
        print("初始化本地登录类")
        if None == userInfo['username'] or '' == userInfo['username'] or None == userInfo['password'] or '' == userInfo['password'] or None == userInfo['schoolName'] or '' == userInfo['schoolName']:
            raise Exception('初始化类失败，请键入完整的参数（用户名，密码，学校名称）')
        self.username = userInfo['username']
        self.password = userInfo['password']
        self.schoolName = userInfo['schoolName']
        self.session = requests.session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; U; Android 8.1.0; zh-cn; BLA-AL00 Build/HUAWEIBLA-AL00) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/57.0.2987.132 MQQBrowser/8.9 Mobile Safari/537.36',
        }
        self.session.headers = headers
        self.login_url = 'https://ccut.campusphere.net/iap/login?service=https%3A%2F%2Fccut.campusphere.net%2Fportal%2Flogin'
        self.host = 'https://ccut.campusphere.net/'
        self.login_host ='https://ccut.campusphere.net/'
        self.loginEntity = None

    # 本地化登陆
    def login(self):
        self.loginEntity = iapLogin(self.username, self.password, self.login_url, self.login_host, self.session)
        self.session.cookies = self.loginEntity.login()

class Collection:
    # 初始化信息收集类
    def __init__(self, todaLoginService: TodayLoginService, userInfo):
        self.session = todaLoginService.session
        self.host = todaLoginService.host
        self.userInfo = userInfo
        self.form = None
        self.collectWid = None
        self.formWid = None
        self.schoolTaskWid = None

    # 查询表单
    def queryForm(self):
        headers = self.session.headers
        headers['Content-Type'] = 'application/json'
        queryUrl = f'{self.host}wec-counselor-collector-apps/stu/collector/queryCollectorProcessingList'
        params = {
            'pageSize': 6,
            "pageNumber": 1
        }
        res = self.session.post(queryUrl, data=json.dumps(params), headers=headers, verify=False).json()
        if len(res['datas']['rows']) < 1:
            raise Exception('查询表单失败，请确认你是信息收集并且当前有收集任务。确定请联系开发者')
        self.collectWid = res['datas']['rows'][0]['wid']
        self.formWid = res['datas']['rows'][0]['formWid']
        detailUrl = f'{self.host}wec-counselor-collector-apps/stu/collector/detailCollector'
        res = self.session.post(detailUrl, headers=headers, data=json.dumps({'collectorWid': self.collectWid}),
                                verify=False).json()
        self.schoolTaskWid = res['datas']['collector']['schoolTaskWid']
        getFormUrl = f'{self.host}wec-counselor-collector-apps/stu/collector/getFormFields'
        params = {"pageSize": 100, "pageNumber": 1, "formWid": self.formWid, "collectorWid": self.collectWid}
        res = self.session.post(getFormUrl, headers=headers, data=json.dumps(params), verify=False).json()
        self.form = res['datas']['rows']

    # 填写表单
    def fillForm(self):
        index = 0
        for formItem in self.form[:]:
            # 只处理必填项
            if formItem['isRequired'] == 1:
                userForm = self.userInfo['forms'][index]['form']
                # 判断用户是否需要检查标题
                if self.userInfo['checkTitle'] == 1:
                    # 如果检查到标题不相等
                    if formItem['title'] != userForm['title']:
                        raise Exception(
                            f'\r\n第{index + 1}个配置项的标题不正确\r\n您的标题为：{userForm["title"]}\r\n系统的标题为：{formItem["title"]}')
                # 文本选项直接赋值
                if formItem['fieldType'] == 1 or formItem['fieldType'] == 5:
                    formItem['value'] = userForm['value']
                # 单选框填充
                elif formItem['fieldType'] == 2:
                    formItem['value'] = userForm['value']
                    # 单选需要移除多余的选项
                    fieldItems = formItem['fieldItems']
                    for fieldItem in fieldItems[:]:
                        if fieldItem['content'] != userForm['value']:
                            fieldItems.remove(fieldItem)
                # 多选填充
                elif formItem['fieldType'] == 3:
                    fieldItems = formItem['fieldItems']
                    userItems = userForm['value'].split('|')
                    for fieldItem in fieldItems[:]:
                        if fieldItem['content'] in userItems:
                            formItem['value'] += fieldItem['content'] + ' '
                        else:
                            fieldItems.remove(fieldItem)
                if formItem['fieldType'] == 4:
                    pass
                index += 1
            else:
                self.form.remove(formItem)

    def submitForm(self):
        extension = {
            "model": "OPPO R11 Plus",
            "appVersion": "8.2.14",
            "systemVersion": "9.1.0",
            "userId": self.userInfo['username'],
            "systemName": "android",
            "lon": self.userInfo['lon'],
            "lat": self.userInfo['lat'],
            "deviceId": str(uuid.uuid1())
        }

        headers = {
            'User-Agent': self.session.headers['User-Agent'],
            'CpdailyStandAlone': '0',
            'extension': '1',
            'Cpdaily-Extension': self.DESEncrypt(json.dumps(extension)),
            'Content-Type': 'application/json; charset=utf-8',
            'Host': re.findall('//(.*?)/', self.host)[0],
            'Connection': 'Keep-Alive',
            'Accept-Encoding': 'gzip'
        }
        params = {
            "formWid": self.formWid, "address": self.userInfo['address'], "collectWid": self.collectWid,
            "schoolTaskWid": self.schoolTaskWid, "form": self.form, "uaIsCpadaily": True
        }
        submitUrl = f'{self.host}wec-counselor-collector-apps/stu/collector/submitForm'
        data = self.session.post(submitUrl, headers=headers, data=json.dumps(params), verify=False).json()
        return data['message']

    # DES加密
    def DESEncrypt(self, content):
        key = 'b3L26XNL'
        iv = b"\x01\x02\x03\x04\x05\x06\x07\x08"
        k = des(key, CBC, iv, pad=None, padmode=PAD_PKCS5)
        encrypt_str = k.encrypt(content)
        return base64.b64encode(encrypt_str).decode()

def getYmlConfig(yaml_file='config.yml'):
    file = open(yaml_file, 'r', encoding="utf-8")
    file_data = file.read()
    file.close()
    config = yaml.load(file_data, Loader=yaml.FullLoader)
    return dict(config)

def main():
    config = getYmlConfig()
    for user in config['users']:
        if config['debug']:
            msg = working(user)
        else:
            try:
                msg = working(user)
            except Exception as e:
                msg = str(e)
        print(msg)

def working(user):
    today = TodayLoginService(user['user'])
    today.login()
    collection = Collection(today, user['user'])
    collection.queryForm()
    collection.fillForm()
    msg = collection.submitForm()
    return msg

if __name__ == '__main__':
    main()
