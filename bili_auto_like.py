from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import json
import time
import random
import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import sys
import os

def init_browser():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("--log-level=3")
    options.add_argument("--window-size=1200,800")
    
    # 跨平台chromedriver路径配置
    base_paths = [
        "",  # 优先使用PATH环境变量中的驱动
        "chromedriver",
        "drivers/chromedriver",
        "/usr/bin/chromedriver",
        "/usr/local/bin/chromedriver"
    ]
    
    # 根据操作系统扩展路径
    if sys.platform.startswith("win"):
        base_paths.extend([
            "chromedriver.exe",
            "drivers/chromedriver.exe",
            r"C:\Program Files\Google\Chrome\Application\chromedriver.exe",
            r"C:\Windows\System32\chromedriver.exe"
        ])
    elif sys.platform == "darwin":  # macOS
        base_paths.extend([
            "/Applications/Google Chrome.app/Contents/MacOS/chromedriver",
            "/usr/local/Caskroom/chromedriver/latest/chromedriver"
        ])
    elif sys.platform.startswith("linux"):
        base_paths.extend([
            "/usr/lib/chromium-browser/chromedriver",
            "/snap/bin/chromedriver"
        ])
    
    # 尝试环境变量指定路径
    env_path = os.environ.get("CHROMEDRIVER_PATH")
    if env_path:
        base_paths.insert(0, env_path)
    
    driver = None
    used_path = ""
    
    for path in base_paths:
        try:
            # 空路径表示使用系统PATH
            service = Service(executable_path=path) if path else Service()
            driver = webdriver.Chrome(service=service, options=options)
            used_path = path if path else "System PATH"
            print(f">>> 使用ChromeDriver: {used_path}")
            break
        except Exception as e:
            error = str(e)
            if "executable needs to be in PATH" in error or "No such file or directory" in error:
                continue  # 路径无效则尝试下一个
            else:
                print(f"!!! 驱动加载失败: {error[:100]}")
                break  # 其他类型错误立即终止
    
    if not driver:
        # 最终尝试系统PATH
        try:
            driver = webdriver.Chrome(options=options)
            print(">>> 使用系统PATH中的ChromeDriver")
        except Exception as e:
            print(f"!!! 无法初始化浏览器: {str(e)}")
            print("请执行以下操作:")
            print("1. 确保已安装Chrome浏览器")
            print("2. 下载对应版本的ChromeDriver: https://chromedriver.chromium.org/")
            print("3. 将驱动放入系统PATH或通过CHROMEDRIVER_PATH环境变量指定路径")
            raise SystemExit("浏览器初始化失败")
    
    return driver

# ===== 配置区域 =====
UP_MID = input("请输入目标用户ID号: ")
COOKIE_PATH = "bili_cookies.json"  # Cookie保存路径
MAX_SCROLL = 100  # 最大滚动次数（控制加载的动态数量）
LIKE_DELAY = (0.2, 0.3)  # 点赞延迟范围（秒）
# ===== Cookie处理 =====
def save_cookies(driver):
    cookies = driver.get_cookies()
    with open(COOKIE_PATH, 'w') as f:
        json.dump(cookies, f)
    print(f">>> Cookie已保存至 {COOKIE_PATH}")

def load_cookies(driver):
    try:
        with open(COOKIE_PATH, 'r') as f:
            cookies = json.load(f)
        
        # 先访问B站域名以设置Cookie
        driver.get("https://www.bilibili.com")
        for cookie in cookies:
            # 修复可能的Cookie格式问题
            if 'sameSite' in cookie and cookie['sameSite'] not in ["Strict", "Lax", "None"]:
                cookie['sameSite'] = "Lax"
            driver.add_cookie(cookie)
        
        print(">>> Cookie加载成功")
        return True
    except FileNotFoundError:
        print("!!! 未找到Cookie文件，请先登录")
        return False

# ===== 登录处理 =====
def manual_login(driver):
    print(">>> 请手动登录B站账号...")
    driver.get("https://passport.bilibili.com/login")
    
    # 等待登录完成
    WebDriverWait(driver, 120).until(
        EC.url_contains("www.bilibili.com")
    )
    
    save_cookies(driver)
    return True

# ===== UP主动态处理 =====
def get_up_dynamic_page(driver, mid):
    """导航到UP主的动态页面"""
    url = f"https://space.bilibili.com/{mid}/dynamic"
    print(f">>> 正在访问UP主动态页: {url}")
    driver.get(url)
    
    # 等待动态加载
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".bili-dyn-list"))
        )
    except TimeoutException:
        print("!!! 动态加载超时，可能页面结构已更改")
        return False
    return True
def scroll_to_load(driver, target_count=6000, max_scroll=600):
    """滚动页面以加载指定数量的动态"""
    print(f">>> 正在加载动态，目标数量: {target_count}")
    scroll_count = 0
    loaded_count = 0
    
    # 初始获取已加载的动态数量
    try:
        cards = driver.find_elements(By.CSS_SELECTOR, ".bili-dyn-item")
        loaded_count = len(cards)
        print(f"  初始已加载动态: {loaded_count}条")
    except NoSuchElementException:
        print("!!! 未找到动态卡片元素")
        return loaded_count
    
    # 滚动加载直到达到目标数量或最大滚动次数
    while loaded_count < target_count and scroll_count < max_scroll:
        # 记录滚动前高度
        prev_height = driver.execute_script("return document.body.scrollHeight")
        
        # 滚动到底部
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        scroll_count += 1
        print(f"  滚动 #{scroll_count}")
        
        # 等待新内容加载（随机延迟）
        time.sleep(random.uniform(0.7, 1.7))
        
        # 获取新高度
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        # 检查是否有新内容加载
        if new_height == prev_height:
            print("  高度未变化，尝试检测加载状态")
            
            # 检查是否显示"没有更多内容"
            try:
                end_text = driver.find_element(
                    By.CSS_SELECTOR, ".bili-dyn-list__end"
                ).text
                if "没有更多动态" in end_text:
                    print(">>> 已加载所有可用动态")
                    break
            except:
                pass
            
            # 检查是否有加载指示器
            try:
                loading = driver.find_element(
                    By.CSS_SELECTOR, ".bili-dyn-list__loading"
                )
                print("  检测到加载指示器，继续等待...")
                time.sleep(0.5)  # 额外等待加载
            except:
                print("  无加载指示器，可能已加载所有内容")
                break
        
        # 获取当前加载的动态数量
        try:
            cards = driver.find_elements(By.CSS_SELECTOR, ".bili-dyn-item")
            new_count = len(cards)
            
            if new_count > loaded_count:
                print(f"  新增 {new_count - loaded_count} 条动态，总计: {new_count}")
                loaded_count = new_count
            else:
                print("  本次滚动未加载新动态")
                
            # 达到目标数量则停止
            if loaded_count >= target_count:
                print(f">>> 已加载目标数量动态: {loaded_count}/{target_count}")
                break
        except:
            print("  获取动态数量失败")
    
    print(f">>> 完成动态加载，滚动次数: {scroll_count}, 总动态数: {loaded_count}")
    return loaded_count
#<div data-module="action" data-type="like" class="bili-dyn-action like active"><svg style="width: 18px; height: 18px;" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 18 18" width="18" height="18"><path d="M15.238949999999999 5.8749875L11.728124999999999 5.8749875C11.903625 5.509125 12.108450000000001 5.0146725 12.179124999999999 4.54079C12.225925 4.227235 12.230549999999997 3.8411524999999997 12.192600000000002 3.4729099999999997C12.155475 3.1126975 12.072274999999998 2.715405 11.909324999999999 2.4065275C11.5572 1.73896 11.07925 1.2830650000000001 10.515075 1.1730275000000001C9.9175 1.056475 9.4 1.3591199999999999 9.086975 1.832795C8.821325 2.2348025 8.71795 2.5693425000000003 8.62185 2.8804925L8.619125 2.8893475C8.526275 3.1897624999999996 8.4337 3.488995 8.19635 3.9093850000000003C7.807925000000001 4.59742 7.489369999999999 4.956485000000001 7.062139999999999 5.331055C6.807695000000001 5.5541375 6.541364999999999 5.6883925 6.3125 5.760025L6.3125 15.85475C6.9202625 15.868200000000002 7.573125 15.876800000000003 8.25 15.876800000000003C10.00675 15.876800000000003 11.4894 15.819474999999999 12.466925 15.767950000000003C13.408750000000001 15.7183 14.305975 15.243900000000002 14.795475 14.385325C15.267499999999998 13.557499999999997 15.871775 12.304749999999999 16.235825000000002 10.807475C16.577575000000003 9.40205 16.719975 8.259725 16.7778 7.4839150000000005C16.846225 6.565215 16.10015 5.8749875 15.238949999999999 5.8749875zM5.3125 15.827525L5.3125 5.8749875L3.9767325000000002 5.8749875C2.8486374999999997 5.8749875 1.8491449999999998 6.6792625 1.7212225 7.843025000000001C1.63766 8.60325 1.5625 9.5917 1.5625 10.6893C1.5625 11.876325000000001 1.6504175 12.977975 1.7415649999999998 13.801975C1.864035 14.909174999999998 2.7766325 15.718875 3.8673275 15.770325C4.28143 15.789874999999999 4.769835 15.810149999999998 5.3125 15.827525z" fill="currentColor"></path></svg>
#  33
#</div>
def like_dynamic(driver, card, index):
    """点赞单个动态 - 基于提供的HTML结构优化"""
    try:
        # 使用特定属性定位点赞按钮
        try:
            like_button = card.find_element(
                By.CSS_SELECTOR, "div[data-module='action'][data-type='like']"
            )
        except NoSuchElementException:
            print(f"    ⚠️ 未找到第 {index} 条动态的点赞按钮")
            return False
        
        # 检查是否已点赞
        is_liked = "active" in like_button.get_attribute("class")
        if is_liked:
            print(f"    ⏩ 第 {index} 条动态已点赞，跳过")
            return False
        
        # 获取当前点赞数（用于验证）
        try:
            before_count = int(like_button.text.strip())
        except:
            before_count = None
        
        # 确保按钮可见
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", like_button)
        time.sleep(0)  # 滚动后短暂等待
        
        # 随机延迟（模拟人类操作）
        #time.sleep(random.uniform(*LIKE_DELAY))
        
        # 点赞操作
        try:
            like_button.click()
        except ElementClickInterceptedException:
            # 如果点击被拦截，使用JavaScript点击
            driver.execute_script("arguments[0].click();", like_button)
        
        # 等待点赞动画
        time.sleep(0.05)
        
        # 验证点赞成功（三种方式）
        success = False
        
        # 方式1: 检查类名变化
        if "active" in like_button.get_attribute("class"):
            success = True
        
        # 方式2: 检查数字变化
        if not success and before_count is not None:
            try:
                after_count = int(like_button.text.strip())
                if after_count == before_count + 1:
                    success = True
            except:
                pass
        
        # 方式3: 检查SVG路径变化
        if not success:
            try:
                svg = like_button.find_element(By.TAG_NAME, "svg")
                d_attribute = svg.find_element(By.TAG_NAME, "path").get_attribute("d")
                # 检查是否是点赞后的SVG路径
                if "M15.238949999999999" in d_attribute:
                    success = True
            except:
                pass
        
        if success:
            print(f"    👍 成功点赞第 {index} 条动态")
            return True
        else:
            print("    ⚠️ 点赞状态验证失败")
            return False
        
    except Exception as e:
        print(f"    ❌ 处理第 {index} 条动态时出错: {str(e)}")
        return False


def like_up_dynamics(driver):
    """点赞UP主所有未点赞的动态 - 优化版"""
    # 获取所有动态卡片
    try:
        cards = driver.find_elements(By.CSS_SELECTOR, ".bili-dyn-item, .dyn-card")
        print(f">>> 找到 {len(cards)} 条动态")
    except NoSuchElementException:
        print("!!! 未找到动态卡片，尝试备用选择器...")
        # 尝试更通用的选择器
        try:
            cards = driver.find_elements(
                By.XPATH, "//div[contains(@class, 'dyn-item') or contains(@class, 'card')]"
            )
            print(f">>> 找到 {len(cards)} 条动态 (备用选择器)")
        except:
            print("!!! 未找到任何动态卡片")
            return 0
    
    liked_count = 0
    processed_count = 371
    
    for i, card in enumerate(cards):
        processed_count += 1
        
        # 跳过无法处理的卡片
        try:
            if not card.is_displayed():
                print(f"    ⏩ 第 {i+1} 条动态不可见，跳过")
                continue
        except StaleElementReferenceException:
            print(f"    ⏩ 第 {i+1} 条动态已失效，跳过")
            continue
        
        # 尝试点赞
        if like_dynamic(driver, card, i+1):
            liked_count += 1
            
            # 点赞间隔
            time.sleep(random.uniform(0.3, 0.5))
    
    print(f">>> 已处理 {processed_count} 条动态，成功点赞 {liked_count} 条")
    return liked_count



# ===== 主函数 =====
def main():
    # 初始化浏览器
    driver = init_browser()
    
    try:
        # 尝试加载Cookie
        if not load_cookies(driver):
            # 手动登录
            if not manual_login(driver):
                print("!!! 登录失败，程序终止")
                return
        
        # 访问UP主动态页
        if not get_up_dynamic_page(driver, UP_MID):
            print("!!! 无法访问UP主动态页")
            return
        
        # 滚动加载动态
        scroll_to_load(driver)
        
        # 点赞所有未点赞动态
        print(">>> 开始点赞...")
        start_time = time.time()
        liked_count = like_up_dynamics(driver)
        elapsed = time.time() - start_time
        
        print(f"\n>>> 操作完成！成功点赞 {liked_count} 条动态")
        print(f">>> 用时: {elapsed:.2f} 秒")
        
    except Exception as e:
        print(f"!!! 发生错误: {str(e)}")
    #finally:
        #driver.quit()
        #print(">>> 浏览器已关闭")

if __name__ == "__main__":
    print("====== B站特定UP主动态点赞脚本 ======")
    print(f"目标UP主: {UP_MID}")
    print("第一次使用需先登陆")
    main()