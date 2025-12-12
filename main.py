import flet as ft
from datetime import datetime
import os
import traceback # 用于捕获错误

def main(page: ft.Page):
    
    # ================= 1. 基础配置 =================
    # 字体逻辑
    font_name = "my_font"
    font_path = "msyh.ttc"
    if not os.path.exists(font_path):
        font_path = "msyh.ttf"
    
    if os.path.exists(font_path):
        page.fonts = {font_name: font_path}
        page.theme = ft.Theme(font_family=font_name)
    else:
        page.theme = ft.Theme()

    page.title = "逆序打卡"
    page.theme_mode = "light"
    page.scroll = "None"
    
    # 【修复UI靠上】禁用页面默认内边距，完全由 SafeArea 控制
    page.padding = 0 

    # ================= 2. 数据处理 =================
    def load_data():
        try:
            data = page.client_storage.get("daka_data")
            if data is None:
                return {"tasks": [], "achievements": []}
            return data
        except:
            return {"tasks": [], "achievements": []}

    def save_data(data):
        try:
            # Flet 的 client_storage 只能存 JSON 可序列化的数据
            # 如果 data 里包含 datetime 对象，这里会直接崩溃
            page.client_storage.set("daka_data", data)
        except Exception as e:
            # 【关键修改】如果保存失败，直接弹红窗告诉你是为什么
            print(f">>> 保存数据失败: {e}")
            page.snack_bar = ft.SnackBar(
                ft.Text(f"【严重】数据保存失败: {e}"), 
                bgcolor="red",
                duration=5000
            )
            page.snack_bar.open = True
            page.update()
            # 抛出异常，中断后面的操作，不要假装成功
            raise e

    app_data = load_data()

    # --- 跨天惩罚逻辑 ---
    def process_penalty_logic():
        try:
            today_str = datetime.now().strftime("%Y-%m-%d")
            today_date = datetime.strptime(today_str, "%Y-%m-%d")
            data_changed = False
            for task in app_data["tasks"]:
                last_inter_str = task.get("last_interaction", today_str)
                last_date = datetime.strptime(last_inter_str, "%Y-%m-%d")
                delta_days = (today_date - last_date).days
                if delta_days > 0:
                    penalty = 0
                    if not task.get("checked_today", False):
                        penalty += 1
                    if delta_days > 1:
                        penalty += (delta_days - 1)
                    if penalty > 0:
                        task['days'] += penalty
                        data_changed = True
                    task['checked_today'] = False
                    task['last_interaction'] = today_str
                    data_changed = True
            if data_changed:
                save_data(app_data)
        except:
            pass

    process_penalty_logic()

    # ================= 3. 业务逻辑 =================
    
    def get_day_color(days):
        if days < 5: return "green"
        elif days < 10: return "blue"
        return "black"

    # 打卡
    def do_check_in(task_id):
        for task in app_data["tasks"]:
            if task['id'] == task_id:
                task['days'] -= 1
                if task['days'] <= 0:
                    app_data["tasks"].remove(task)
                    app_data["achievements"].append({
                        "name": task['name'],
                        "target": task.get('original_target', 0),
                        "created_at": task.get('created_at', datetime.now().strftime("%Y-%m-%d")),
                        "finished_at": datetime.now().strftime("%Y-%m-%d")
                    })
                    page.snack_bar = ft.SnackBar(ft.Text(f"恭喜！任务 {task['name']} 已完成！"))
                    page.snack_bar.open = True
                else:
                    task['checked_today'] = True
                    task['last_interaction'] = datetime.now().strftime("%Y-%m-%d")
                
                save_data(app_data)
                render_main_page()
                break

    # 添加任务 (带详细调试信息)
    def do_add_task(name, days_str):
        try:
            if not days_str.isdigit():
                page.snack_bar = ft.SnackBar(ft.Text("天数必须是纯数字！"))
                page.snack_bar.open = True
                page.update()
                return

            days = int(days_str)
            
            # 【注意检查这里】
            # timestamp 生成的是 float，str() 后没问题
            # 确保这里面没有 datetime 对象，全都是 str/int/bool
            new_task = {
                "id": str(datetime.now().timestamp()),
                "name": str(name), # 强制转字符串，防止特殊类型
                "days": days,
                "original_target": days,
                "created_at": datetime.now().strftime("%Y-%m-%d"), # 已经是字符串
                "last_interaction": datetime.now().strftime("%Y-%m-%d"), # 已经是字符串
                "checked_today": False
            }
            
            # 先打印一下，看看数据结构对不对
            print(f">>> 准备保存的新任务: {new_task}")

            app_data["tasks"].append(new_task)
            
            # 这里调用上面修改过的 save_data
            # 如果保存失败，这里会报错并跳到 except
            save_data(app_data)
            
            # 如果能走到这一步，说明保存成功了
            render_main_page(msg="任务创建成功！")
            
        except Exception as e:
            # 这里会捕获 save_data 抛出的异常
            import traceback
            traceback.print_exc()
            
            # 再次强制弹窗，确保你能看到
            page.snack_bar = ft.SnackBar(
                ft.Text(f"创建流程中断: {str(e)}"), 
                bgcolor="red",
                duration=5000
            )
            page.snack_bar.open = True
            page.update()
            
        except Exception as e:
            print(">>> do_add_task 内部报错:") # Debug
            traceback.print_exc() # Debug
            page.snack_bar = ft.SnackBar(ft.Text(f"创建失败: {str(e)}"))
            page.snack_bar.open = True
            page.update()

    # ================= 4. UI 渲染 (加入 SafeArea) =================
    
    # --- 场景 A: 主页 ---
    def render_main_page(e=None, msg=None):
        try:
            page.clean()
            
            tasks_column = ft.Column(spacing=10, scroll="auto")
            
            if not app_data["tasks"]:
                tasks_column.controls.append(
                    ft.Container(
                        content=ft.Text("暂无任务，请点击右下角 + 号", color="grey", size=16),
                        alignment=ft.alignment.center,
                        padding=20
                    )
                )

            today_str = datetime.now().strftime("%Y-%m-%d")
            for task in app_data["tasks"]:
                is_done_today = task.get("checked_today", False) and task.get("last_interaction") == today_str
                btn_text = "已完成" if is_done_today else "打卡"
                btn_bg = "grey" if is_done_today else "teal"
                
                def on_click_checkin(e, t_id=task['id']):
                    do_check_in(t_id)

                task_card = ft.Card(
                    elevation=2,
                    content=ft.Container(
                        height=90,
                        padding=ft.padding.symmetric(horizontal=15),
                        content=ft.Stack(
                            controls=[
                                ft.Container(
                                    content=ft.Text(str(task['name']), size=16, weight="bold", max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                    alignment=ft.alignment.center_left,
                                    width=100,
                                ),
                                ft.Container(
                                    content=ft.Row(
                                        [
                                            ft.Text(str(task['days']), size=42, weight="bold", color=get_day_color(task['days'])),
                                            ft.Container(content=ft.Text("天", size=14, color="grey"), padding=ft.padding.only(top=14))
                                        ],
                                        alignment=ft.MainAxisAlignment.CENTER, spacing=2, tight=True
                                    ),
                                    alignment=ft.alignment.center,
                                ),
                                ft.Container(
                                    content=ft.ElevatedButton(text=btn_text, disabled=is_done_today, bgcolor=btn_bg, color="white", width=85, style=ft.ButtonStyle(padding=5), on_click=on_click_checkin),
                                    alignment=ft.alignment.center_right
                                )
                            ]
                        )
                    )
                )
                tasks_column.controls.append(task_card)

            achievements_column = ft.Column(spacing=10, scroll="auto")
            for ach in app_data["achievements"]:
                created_at = ach.get('created_at', '?')
                finished_at = ach.get('finished_at', '?')
                achievements_column.controls.append(
                    ft.ListTile(
                        leading=ft.Icon("emoji_events", color="amber"),
                        title=ft.Text(f"{ach['name']}", weight="bold"),
                        subtitle=ft.Text(f"周期: {created_at} 至 {finished_at}", size=12),
                    )
                )

            tabs = ft.Tabs(
                selected_index=0,
                tabs=[
                    ft.Tab(text="进行中", icon="list", content=ft.Container(content=tasks_column, padding=10)),
                    ft.Tab(text="成就墙", icon="emoji_events", content=ft.Container(content=achievements_column, padding=10)),
                ],
                expand=1,
            )

            page.add(
                ft.SafeArea(
                    ft.Container(
                        content=tabs,
                        padding=10
                    )
                )
            )
            
            page.floating_action_button = ft.FloatingActionButton(icon="add", bgcolor="teal", on_click=render_add_page)
            
            if msg:
                page.snack_bar = ft.SnackBar(ft.Text(msg))
                page.snack_bar.open = True
            
            page.update()
            
        except Exception as e:
            print(">>> render_main_page 渲染错误:") # Debug
            print(traceback.format_exc()) # Debug
            page.add(ft.Text(f"渲染错误: {e}", color="red"))
            page.update()

    # --- 场景 B: 添加页 ---
   # --- 场景 B: 添加页 (带屏幕日志版) ---
    def render_add_page(e=None):
        page.clean()
        page.floating_action_button = None
        
        name_field = ft.TextField(label="任务名称", autofocus=True)
        days_field = ft.TextField(label="目标天数 (纯数字)", keyboard_type="number")
        
        # === 新增：屏幕上的日志显示区 ===
        log_column = ft.Column(scroll="always", height=200) # 给它高度，允许滚动
        
        def screen_log(msg):
            """把日志直接写在手机屏幕上"""
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_msg = f"[{timestamp}] {msg}"
            print(log_msg) # 同时也尝试打印到后台
            
            # 添加红色的字到屏幕上
            log_column.controls.insert(0, ft.Text(log_msg, color="red", size=12, font_family="monospace"))
            try:
                page.update()
            except:
                pass

        def on_confirm(e):
            screen_log(">>> 按钮被点击，开始执行...")
            e.control.text = "运行中..."
            e.control.bgcolor = "orange"
            e.control.update()

            try:
                # 1. 校验
                if not name_field.value:
                    screen_log("❌ 失败: 名字为空")
                    name_field.error_text = "请输入任务名称"
                    page.update()
                    return
                if not days_field.value:
                    screen_log("❌ 失败: 天数为空")
                    days_field.error_text = "请输入目标天数"
                    page.update()
                    return
                
                screen_log("✅ 校验通过")
                
                # 2. 准备数据
                days = int(days_field.value)
                new_task = {
                    "id": str(datetime.now().timestamp()),
                    "name": str(name_field.value),
                    "days": days,
                    "original_target": days,
                    "created_at": datetime.now().strftime("%Y-%m-%d"),
                    "last_interaction": datetime.now().strftime("%Y-%m-%d"),
                    "checked_today": False
                }
                screen_log(f"📋 数据已生成: {new_task['name']}")

                # 3. 尝试写入内存
                app_data["tasks"].append(new_task)
                screen_log("💾 已追加到内存列表")

                # 4. 尝试保存到手机存储 (最容易崩的地方)
                screen_log("⏳ 正在调用 client_storage...")
                # ------------------------------------------------
                # 临时测试：如果你怀疑是存储坏了，把下面这行注释掉试试
                page.client_storage.set("daka_data", app_data)
                # ------------------------------------------------
                screen_log("✅ client_storage 保存成功！")
                
                # 5. 跳转
                screen_log("🚀 准备跳转回主页...")
                import time
                time.sleep(1) # 故意停顿1秒让你看清日志
                render_main_page(msg="任务创建成功！")
                
            except Exception as err:
                # 如果崩了，这里会显示详细原因
                import traceback
                err_str = traceback.format_exc()
                screen_log(f"💥 严重崩溃: {str(err)}")
                screen_log(f"详情: {err_str}") # 把堆栈也打出来

        def on_cancel(e):
            render_main_page()
            
        content_column = ft.Column(
            [
                ft.Icon(ft.Icons.ADD_TASK, size=64, color="teal"),
                ft.Text("新建挑战 (调试模式)", size=24, weight="bold"),
                name_field,
                days_field,
                ft.Row([
                    ft.ElevatedButton("取消", on_click=on_cancel),
                    ft.ElevatedButton("确定创建", on_click=on_confirm, bgcolor="teal", color="white"),
                ], alignment="center"),
                ft.Divider(),
                ft.Text("--- 下面是运行日志 ---", size=10, color="grey"),
                ft.Container(
                    content=log_column,
                    bgcolor=ft.colors.GREY_100,
                    border=ft.border.all(1, "grey"),
                    padding=10,
                    border_radius=5
                )
            ],
            scroll="auto"
        )
        
        page.add(ft.SafeArea(ft.Container(content=content_column, padding=20, expand=True)))
        page.update()

    render_main_page()

if __name__ == "__main__":
    ft.app(target=main)



