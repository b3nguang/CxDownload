import os
import time
import json
import random
import requests
from bs4 import BeautifulSoup
from hashlib import md5
from requests.adapters import HTTPAdapter

from api.cipher import AESCipher
from api.logger import logger
from api.cookies import save_cookies, use_cookies
from api.config import GlobalConst as gc
from api.decode import (
    decode_course_list,
    decode_course_point,
    decode_course_card,
    decode_course_folder,
)


def get_timestamp():
    return str(int(time.time() * 1000))


def get_random_seconds():
    return random.randint(30, 90)


def init_session(isVideo: bool = False, isAudio: bool = False):
    _session = requests.session()
    _session.verify = False
    _session.mount("http://", HTTPAdapter(max_retries=3))
    _session.mount("https://", HTTPAdapter(max_retries=3))
    if isVideo:
        _session.headers = gc.VIDEO_HEADERS
    elif isAudio:
        _session.headers = gc.AUDIO_HEADERS
    else:
        _session.headers = gc.HEADERS
    _session.cookies.update(use_cookies())
    return _session


class Account:
    username = None
    password = None
    last_login = None
    isSuccess = None

    def __init__(self, _username, _password):
        self.username = _username
        self.password = _password


class Chaoxing:
    def __init__(self, account: Account = None):
        self.account = account
        self.cipher = AESCipher()

    def login(self):
        _session = requests.session()
        _session.verify = False
        _url = "https://passport2.chaoxing.com/fanyalogin"
        _data = {
            "fid": "-1",
            "uname": self.cipher.encrypt(self.account.username),
            "password": self.cipher.encrypt(self.account.password),
            "refer": "https%3A%2F%2Fi.chaoxing.com",
            "t": True,
            "forbidotherlogin": 0,
            "validate": "",
            "doubleFactorLogin": 0,
            "independentId": 0,
        }
        logger.trace("正在尝试登录...")
        resp = _session.post(_url, headers=gc.HEADERS, data=_data)
        if resp and resp.json()["status"] == True:
            save_cookies(_session)
            logger.info("登录成功...")
            return {"status": True, "msg": "登录成功"}
        else:
            return {"status": False, "msg": str(resp.json()["msg2"])}

    def get_fid(self):
        _session = init_session()
        return _session.cookies.get("fid")

    def get_uid(self):
        _session = init_session()
        return _session.cookies.get("_uid")

    def get_course_list(self):
        _session = init_session()
        _url = "https://mooc2-ans.chaoxing.com/mooc2-ans/visit/courselistdata"
        _data = {"courseType": 1, "courseFolderId": 0, "query": "", "superstarClass": 0}
        logger.trace("正在读取所有的课程列表...")
        # 接口突然抽风, 增加headers
        _headers = {
            "Host": "mooc2-ans.chaoxing.com",
            "sec-ch-ua-platform": '"Windows"',
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
            "Accept": "text/html, */*; q=0.01",
            "sec-ch-ua": '"Microsoft Edge";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "sec-ch-ua-mobile": "?0",
            "Origin": "https://mooc2-ans.chaoxing.com",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Referer": "https://mooc2-ans.chaoxing.com/mooc2-ans/visit/interaction?moocDomain=https://mooc1-1.chaoxing.com/mooc-ans",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,ja;q=0.5",
        }
        _resp = _session.post(_url, headers=_headers, data=_data)
        # logger.trace(f"原始课程列表内容:\n{_resp.text}")
        logger.info("课程列表读取完毕...")
        course_list = decode_course_list(_resp.text)

        _interaction_url = "https://mooc2-ans.chaoxing.com/mooc2-ans/visit/interaction"
        _interaction_resp = _session.get(_interaction_url)
        course_folder = decode_course_folder(_interaction_resp.text)
        for folder in course_folder:
            _data = {
                "courseType": 1,
                "courseFolderId": folder["id"],
                "query": "",
                "superstarClass": 0,
            }
            _resp = _session.post(_url, data=_data)
            course_list += decode_course_list(_resp.text)
        return course_list

    def get_course_point(self, _courseid, _clazzid, _cpi):
        _session = init_session()
        _url = f"https://mooc2-ans.chaoxing.com/mooc2-ans/mycourse/studentcourse?courseid={_courseid}&clazzid={_clazzid}&cpi={_cpi}&ut=s"
        logger.trace("开始读取课程所有章节...")
        _resp = _session.get(_url)
        # logger.trace(f"原始章节列表内容:\n{_resp.text}")
        logger.info("课程章节读取成功...")
        return decode_course_point(_resp.text)

    def get_job_list(self, _clazzid, _courseid, _cpi, _knowledgeid):
        _session = init_session()
        job_list = []
        job_info = {}

        download_dir = "downloads"

    # 确保目录存在
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)


        for _possible_num in [
            "0",
            "1",
            "2",
        ]:  # 学习界面任务卡片数, 很少有3个的, 但是对于章节解锁任务点少一个都不行, 可以从API /mooc-ans/mycourse/studentstudyAjax获取值, 或者干脆直接加, 但二者都会造成额外的请求
            _url = f"https://mooc1.chaoxing.com/mooc-ans/knowledge/cards?clazzid={_clazzid}&courseid={_courseid}&knowledgeid={_knowledgeid}&num={_possible_num}&ut=s&cpi={_cpi}&v=20160407-3&mooc2=1"
            logger.trace("开始读取章节所有任务点...")
            _resp = _session.get(_url)
            # 解析 HTML 内容
            soup = BeautifulSoup(_resp.text, 'html.parser')
            tmp = soup.find_all("iframe", {"class": "ans-module ans-insertdoc-retract ans-attach-online"})
            
            if not tmp:  # Skip if tmp is empty
                logger.warning("未找到任何课件，跳过...")
                continue
            
            try:
                # print(tmp[0])
                element = tmp[0]
                data_str = element.get('data')
                # 将data属性对应的字符串解析为字典
                data_dict = json.loads(data_str)
                # print(data_dict)
                objectid_value = data_dict.get('objectid')
                filename = data_dict.get('name')
                logger.info(f"检测到课件 {filename}")

                mid_url = f"https://mooc1.chaoxing.com/ananas/status/{objectid_value}?flag=normal&_dc={int(time.time()*1000)}"
                # print(mid_url)
                _headers = {
                    "Accept": "*/*",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
                    "Connection": "keep-alive",
                    "Host": "mooc1.chaoxing.com",
                    "Referer": "https://mooc1.chaoxing.com/ananas/modules/pdf/index.html?v=2024-1224-1153",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-origin",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
                    "X-Requested-With": "XMLHttpRequest",
                    "sec-ch-ua": '"Microsoft Edge";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"',
                }
                mid_resp = _session.get(mid_url,headers=_headers)
                download_url = mid_resp.json()['download']
                logger.info(f"下载地址: {download_url}")

                _download_headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
                    'Accept': '*/*',
                    'Accept-Encoding': 'gzip, deflate, br, zstd',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache',
                    'Referer': 'https://mooc1.chaoxing.com/ananas/modules/pdf/index.html?v=2024-1224-1153',
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-origin',
                    'X-Requested-With': 'XMLHttpRequest',
                    'sec-ch-ua': '"Microsoft Edge";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"Windows"',
                }

                _resp = _session.get(download_url, headers=_download_headers)
                with open(f"{download_dir}/{filename}", "wb") as f:
                    for chunk in _resp.iter_content(8192):
                        f.write(chunk)
                logger.info(f"下载完成: {download_dir}/{filename}")
            except Exception as e:
                logger.error(f"解析任务点时出错: {e}")
                pass

            _job_list, _job_info = decode_course_card(_resp.text)
            if _job_info.get("notOpen", False):
                # 直接返回, 节省一次请求
                logger.info("该章节未开放")
                return [], _job_info
            job_list += _job_list
            job_info.update(_job_info)

        logger.info("章节任务点读取成功...")
        return job_list, job_info

    def get_enc(self, clazzId, jobid, objectId, playingTime, duration, userid):
        return md5(
            f"[{clazzId}][{userid}][{jobid}][{objectId}][{playingTime * 1000}][d_yHJ!$pdA~5][{duration * 1000}][0_{duration}]".encode()
        ).hexdigest()
