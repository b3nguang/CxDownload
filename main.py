import random
import time
import sys
from urllib3 import disable_warnings, exceptions
from api.logger import logger
from api.base import Chaoxing, Account
from api.exceptions import LoginError, FormatError, MaxRollBackError

disable_warnings(exceptions.InsecureRequestWarning)


class RollBackManager:
    def __init__(self):
        self.rollback_times = 0
        self.rollback_id = ""

    def add_times(self, id):
        if id == self.rollback_id:
            self.rollback_times += 1
            if self.rollback_times > 3:
                raise MaxRollBackError("回滚次数已达3次, 请手动检查学习通任务点完成情况")
        else:
            self.rollback_id = id
            self.rollback_times = 1


def get_user_input(prompt):
    try:
        return input(prompt)
    except Exception as e:
        logger.error(f"输入异常: {e}")
        sys.exit(1)


def main():
    try:
        rollback_manager = RollBackManager()
        username = get_user_input("请输入你的手机号, 按回车确认\n手机号:")
        password = get_user_input("请输入你的密码, 按回车确认\n密码:")

        account = Account(username, password)
        chaoxing = Chaoxing(account=account)
        login_state = chaoxing.login()

        if not login_state["status"]:
            raise LoginError(login_state["msg"])

        all_courses = chaoxing.get_course_list()
        logger.info(f"总课程数量: {len(all_courses)}")

        course_list = get_user_input("请输入想要学习的课程列表,以逗号分隔,例: 2151141,189191,198198\n")
        course_ids = course_list.split(",") if course_list else []

        course_task = [course for course in all_courses if course["courseId"] in course_ids] or all_courses
        logger.info(f"课程列表过滤完毕, 当前课程任务数量: {len(course_task)}")

        for course in course_task:
            logger.info(f"开始学习课程: {course['title']}")
            points = chaoxing.get_course_point(course["courseId"], course["clazzId"], course["cpi"])

            for index, point in enumerate(points["points"]):
                logger.info(f'当前章节: {point["title"]}')
                sleep_duration = random.uniform(1, 3)
                logger.debug(f"本次随机等待时间: {sleep_duration}")
                time.sleep(sleep_duration)

                jobs, _ = chaoxing.get_job_list(
                    course["clazzId"], course["courseId"], course["cpi"], point["id"]
                )

                if not jobs:
                    logger.warning(f"章节 {point['title']} 无任务点")

        logger.info("所有课件下载任务已完成")

    except LoginError as e:
        logger.error(f"登录失败: {e}")
    except FormatError as e:
        logger.error(f"格式错误: {e}")
    except MaxRollBackError as e:
        logger.error(f"回滚错误: {e}")
    except Exception as e:
        logger.error(f"未处理的错误: {e}")
        import traceback

        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
