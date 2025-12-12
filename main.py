import flet as ft
from datetime import datetime
import traceback
import time

def main(page: ft.Page):
    
    # ================= 1. 基础配置 =================
    page.title = "逆序打卡"
    page.theme_mode = "light"
    # 【一加13适配】禁止整页滚动，防止布局冲突
    page.scroll = None 
    page.padding = 0 
    page.theme = ft.Theme()

    # ================= 2. 数据层 =================
    def load_data():
        try:
            data = page.client_storage.get("daka_data")
            if data is None:
                return {"tasks": [], "achievements": []}
            return data
        except Exception:
            # 如果读取失败，返回空结构，防止白屏
            return {"tasks": [], "achievements": []}

    def save_data(data):
        # 这里不弹窗了，把错误抛出去让 UI 层处理
        page.client_storage.set("daka_data", data)

    # 初始化
    app_data = load_data()

    # 跨天逻辑
    def process_penalty_logic():
        try:
            today_str = datetime.now().strftime("%Y-%m-%d")
            today_date = datetime.strptime(today_str, "%Y-%m-%d")
            data_changed = False
            
            # 容错处理：确保 tasks 存在
            if "tasks" not in app_data: app_data["tasks"] = []

            for task in app_data["tasks"]:
                last_inter_str = task.get("last_interaction", today_str)
                if not last_inter_str: last_inter_str = today_str
                last_date = datetime.strptime(last_inter_str, "%Y-%m-%d")
                delta_days = (today_date - last_date).days
                if delta_days > 0:
                    penalty = 0
                    if not task.get("checked_today", False): penalty += 1
                    if delta_days > 1: penalty += (delta_days - 1)
                    if penalty > 0:
                        task['days'] += penalty
                        data_changed = True
                    task['checked_today'] = False
                    task['last_interaction'] = today_str
                    data_changed = True
            if data_changed: save_data(app_data)
        except: pass

    process_penalty_logic()

    # ================= 3. 业务逻辑 =================
    def get_day_color(days):
        if days < 5: return "green"
        elif days < 10: return "blue"
        return "black"

    def do_check_in(task_id):
        try:
            for task in app_data["tasks"]:
                if task['id'] == task_id:
                    task['days'] -= 1
                    if task['days'] <= 0:
                        app_data["tasks"].remove(task)
                        if "achievements" not in app_data: app_data["achievements"] = []
                        app_data["achievements"].insert(0, {
                            "name": task['name'],
                            "created_at": task.get('created_at', '?'),
                            "finished_at": datetime.now().strftime("%Y-%m-%d")
                        })
                        page.snack_bar = ft.SnackBar(ft.Text(f"🎉 {task['name']} 已完成！"))
                        page.snack_bar.open = True
                    else:
                        task['checked_today'] = True
                        task['last_interaction'] = datetime.now().strftime("%Y-%m-%d")
                    save_data(app_data)
                    render_main_page(reload_from_disk=True)
                    break
        except Exception as e:
            page.snack_bar = ft.SnackBar(ft.Text(f"错误: {e}"), bgcolor="red")
            page.snack_bar.open = True
            page.update()

    # ================= 4. UI 渲染 =================
    def render_main_page(e=None, msg=None, reload_from_disk=False):
        try:
            if reload_from_disk:
                fresh_data = load_data()
                app_data.clear()
                app_data.update(fresh_data)

            page.clean()
            
            # --- 任务列表 ---
            tasks_list = ft.ListView(expand=True, spacing=10, padding=10)
            if not app_data.get("tasks"):
                tasks_list.controls.append(
                    ft.Container(content=ft.Text("暂无挑战，点 + 号开启", color="grey"), alignment=ft.alignment.center, padding=40)
                )
            else:
                today_str = datetime.now().strftime("%Y-%m-%d")
                for task in app_data["tasks"]:
                    try:
                        t_id = task.get('id')
                        t_name = str(task.get('name', '任务'))
                        t_days = task.get('days', 0)
                        is_done = task.get("checked_today", False) and task.get("last_interaction") == today_str
                        
                        def on_click_checkin(e, t_id=t_id):
                            do_check_in(t_id)

                        card = ft.Card(
                            elevation=2,
                            content=ft.Container(
                                padding=15,
                                content=ft.Row([
                                    ft.Column([
                                        ft.Text(t_name, size=18, weight="bold"),
                                        ft.Text(f"剩余 {t_days} 天", color=get_day_color(t_days))
                                    ], expand=True),
                                    ft.ElevatedButton(
                                        "已完成" if is_done else "打卡",
                                        disabled=is_done,
                                        bgcolor="grey" if is_done else "teal",
                                        color="white",
                                        on_click=on_click_checkin
                                    )
                                ])
                            )
                        )
                        tasks_list.controls.append(card)
                    except: continue

            # --- 成就墙 ---
            achieve_list = ft.ListView(expand=True, spacing=10, padding=10)
            if app_data.get("achievements"):
                for ach in app_data["achievements"]:
                    achieve_list.controls.append(
                        ft.Card(
                            elevation=1,
                            content=ft.ListTile(
                                leading=ft.Icon(ft.Icons.EMOJI_EVENTS, color="amber"),
                                title=ft.Text(f"{ach.get('name','未知')}", weight="bold"),
                                subtitle=ft.Text(f"完成于: {ach.get('finished_at','?')}", size=12),
                            )
                        )
                    )
            else:
                achieve_list.controls.append(
                    ft.Container(content=ft.Text("还没有成就", color="grey"), alignment=ft.alignment.center, padding=40)
                )

            # --- Tabs ---
            tabs = ft.Tabs(
                selected_index=0,
                animation_duration=0,
                tabs=[
                    ft.Tab(text="进行中", icon=ft.Icons.LIST, content=tasks_list),
                    ft.Tab(text="成就墙", icon=ft.Icons.EMOJI_EVENTS, content=achieve_list),
                ],
                expand=True,
            )

            page.add(
                ft.SafeArea(
                    ft.Column([
                        ft.Container(height=10),
                        ft.Text("  逆序打卡", size=26, weight="bold", color="teal"),
                        ft.Divider(height=1, thickness=1),
                        tabs
                    ], expand=True) 
                )
            )

            page.floating_action_button = ft.FloatingActionButton(
                icon=ft.Icons.ADD, bgcolor="teal", on_click=render_add_page
            )
            
            if msg:
                page.snack_bar = ft.SnackBar(ft.Text(msg))
                page.snack_bar.open = True
            
            page.update()
            
        except Exception as e:
            page.clean()
            page.add(ft.Text(f"渲染崩溃: {e}", color="red"))
            page.update()

    # ================= 5. 添加页 (带诊断功能) =================
    def render_add_page(e=None):
        page.clean()
        page.floating_action_button = None
        
        name_field = ft.TextField(label="任务名称", autofocus=False)
        days_field = ft.TextField(label="天数 (数字)", keyboard_type="number")
        
        # --- 诊断日志区 (专门解决“没反应”的问题) ---
        log_text = ft.Text("准备就绪...", color="grey", size=12)
        
        def update_log(msg, color="black"):
            print(msg) # 打印到后台
            log_text.value = f"{datetime.now().strftime('%H:%M:%S')} - {msg}"
            log_text.color = color
            log_text.update()

        # --- 强力清理按钮 ---
        def clear_cache(e):
            try:
                page.client_storage.clear()
                # 重置内存
                app_data["tasks"] = []
                app_data["achievements"] = []
                update_log("缓存已强制清空！旧数据已删除。", "green")
            except Exception as ex:
                update_log(f"清空失败: {ex}", "red")

        def on_confirm(e):
            update_log("正在检测输入...", "blue")
            
            if not name_field.value:
                update_log("❌ 错误：任务名称不能为空", "red")
                return
            if not days_field.value:
                update_log("❌ 错误：天数不能为空", "red")
                return

            try:
                update_log("正在构建数据...", "blue")
                
                # 构造新任务
                new_task = {
                    "id": str(datetime.now().timestamp()),
                    "name": str(name_field.value),
                    "days": int(days_field.value),
                    "original_target": int(days_field.value),
                    "created_at": str(datetime.now().strftime("%Y-%m-%d")),
                    "last_interaction": str(datetime.now().strftime("%Y-%m-%d")),
                    "checked_today": False
                }
                
                # 确保内存列表存在
                if "tasks" not in app_data: app_data["tasks"] = []
                app_data["tasks"].append(new_task)
                
                update_log("正在写入存储...", "blue")
                save_data(app_data)
                
                update_log("✅ 成功！正在跳转...", "green")
                time.sleep(0.5) # 让你看清成功提示
                render_main_page(msg="任务创建成功！", reload_from_disk=True)
                
            except Exception as ex:
                # 把最底层的错误显示出来！
                traceback.print_exc()
                update_log(f"💥 严重崩溃: {str(ex)}", "red")

        def on_cancel(e):
            render_main_page()

        page.add(
            ft.SafeArea(
                ft.Container(
                    padding=30,
                    content=ft.Column([
                        ft.Icon(ft.Icons.ADD_TASK, size=80, color="teal"),
                        ft.Container(height=20),
                        name_field,
                        ft.Container(height=20),
                        days_field,
                        ft.Container(height=20),
                        
                        # 日志显示区 (防止键盘遮挡 SnackBar)
                        ft.Container(
                            content=log_text,
                            bgcolor=ft.colors.GREY_100,
                            padding=10,
                            border_radius=5,
                            width=300
                        ),
                        
                        ft.Container(height=20),
                        ft.Row([
                            ft.ElevatedButton("取消", on_click=on_cancel),
                            ft.ElevatedButton("创建", on_click=on_confirm, bgcolor="teal", color="white"),
                        ], alignment="center"),
                        
                        ft.Container(height=30),
                        ft.Divider(),
                        ft.TextButton("⚠️如果一直创建失败，点我清空缓存", on_click=clear_cache, style=ft.ButtonStyle(color="red"))
                    ], horizontal_alignment="center", scroll="auto")
                )
            )
        )
        page.update()

    render_main_page()

if __name__ == "__main__":
    ft.app(target=main)
