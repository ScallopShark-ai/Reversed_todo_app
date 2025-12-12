import flet as ft
from datetime import datetime
import traceback
import time

def main(page: ft.Page):
    
    # ================= 1. 基础配置 =================
    page.title = "逆序打卡"
    page.theme_mode = "light"
    # 【保持原样】
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
        except Exception as e:
            return {"tasks": [], "achievements": []}

    def save_data(data):
        try:
            page.client_storage.set("daka_data", data)
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"存储异常: {str(e)}"), 
                bgcolor="red",
                duration=5000
            )
            page.snack_bar.open = True
            page.update()

    app_data = load_data()

    # 跨天逻辑
    def process_penalty_logic():
        try:
            today_str = datetime.now().strftime("%Y-%m-%d")
            today_date = datetime.strptime(today_str, "%Y-%m-%d")
            data_changed = False
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
                        # 任务完成
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

    def do_add_task(name, days_str):
        try:
            if not days_str.isdigit():
                page.snack_bar = ft.SnackBar(ft.Text("天数必须是纯数字"))
                page.snack_bar.open = True
                page.update()
                return

            days = int(days_str)
            new_task = {
                "id": str(datetime.now().timestamp()),
                "name": str(name),
                "days": int(days),
                "original_target": int(days),
                "created_at": str(datetime.now().strftime("%Y-%m-%d")),
                "last_interaction": str(datetime.now().strftime("%Y-%m-%d")),
                "checked_today": False
            }
            app_data["tasks"].append(new_task)
            save_data(app_data)
            render_main_page(msg="创建成功", reload_from_disk=True)
            
        except Exception as e:
            traceback.print_exc()
            page.snack_bar = ft.SnackBar(ft.Text(f"创建崩溃: {e}"), bgcolor="red")
            page.snack_bar.open = True
            page.update()

    # --- 新增：删除功能 ---
    def do_delete_task(task_id):
        try:
            for task in app_data["tasks"]:
                if task['id'] == task_id:
                    app_data["tasks"].remove(task)
                    save_data(app_data)
                    render_main_page(msg="🗑️ 任务已删除", reload_from_disk=True)
                    break
        except Exception as e:
            page.snack_bar = ft.SnackBar(ft.Text(f"删除失败: {e}"), bgcolor="red")
            page.snack_bar.open = True
            page.update()

    def do_delete_achievement(ach_data):
        try:
            if ach_data in app_data["achievements"]:
                app_data["achievements"].remove(ach_data)
                save_data(app_data)
                render_main_page(msg="🗑️ 记录已删除", reload_from_disk=True)
        except Exception as e:
            page.snack_bar = ft.SnackBar(ft.Text(f"删除失败: {e}"), bgcolor="red")
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
            
            # --- 1. 任务列表 (带删除按钮) ---
            tasks_list = ft.ListView(expand=True, spacing=10, padding=10)
            if not app_data["tasks"]:
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
                        
                        # 新增：删除任务的点击事件
                        def on_click_delete(e, t_id=t_id):
                            do_delete_task(t_id)

                        card = ft.Card(
                            elevation=2,
                            content=ft.Container(
                                padding=15,
                                content=ft.Row([
                                    ft.Column([
                                        ft.Text(t_name, size=18, weight="bold"),
                                        ft.Text(f"剩余 {t_days} 天", color=get_day_color(t_days))
                                    ], expand=True),
                                    # 新增：删除按钮
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINE, 
                                        icon_color="red", 
                                        tooltip="删除任务",
                                        on_click=on_click_delete
                                    ),
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

            # --- 2. 成就墙 (带删除按钮) ---
            achieve_list = ft.ListView(expand=True, spacing=10, padding=10)
            if app_data.get("achievements"):
                for ach in app_data["achievements"]:
                    try:
                        # 新增：删除成就的点击事件
                        # 使用闭包锁定当前 ach 对象
                        def on_click_del_ach(e, a=ach):
                            do_delete_achievement(a)

                        achieve_list.controls.append(
                            ft.Card(
                                elevation=1,
                                content=ft.ListTile(
                                    leading=ft.Icon(ft.Icons.EMOJI_EVENTS, color="amber"),
                                    title=ft.Text(f"{ach.get('name','未知')}", weight="bold"),
                                    subtitle=ft.Text(f"完成于: {ach.get('finished_at','?')}", size=12),
                                    # 新增：尾部删除按钮
                                    trailing=ft.IconButton(
                                        ft.Icons.DELETE_OUTLINE, 
                                        icon_color="grey", 
                                        tooltip="删除记录",
                                        on_click=on_click_del_ach
                                    )
                                )
                            )
                        )
                    except: continue
            else:
                achieve_list.controls.append(
                    ft.Container(content=ft.Text("还没有成就，加油！", color="grey"), alignment=ft.alignment.center, padding=40)
                )

            # --- 3. Tabs ---
            tabs = ft.Tabs(
                selected_index=0,
                animation_duration=300,
                tabs=[
                    ft.Tab(text="进行中", icon=ft.Icons.LIST, content=tasks_list),
                    ft.Tab(text="成就墙", icon=ft.Icons.EMOJI_EVENTS, content=achieve_list),
                ],
                expand=True, 
            )

            page.floating_action_button = ft.FloatingActionButton(
                icon="add", bgcolor="teal", on_click=render_add_page
            )
            
            page.add(
                ft.SafeArea(
                    ft.Column([
                        ft.Container(height=10), 
                        ft.Text("  逆序打卡", size=28, weight="bold", color="teal"),
                        ft.Divider(),
                        ft.Container(
                            content=tabs,
                            expand=True 
                        )
                    ], expand=True) 
                )
            )
            
            if msg:
                page.snack_bar = ft.SnackBar(ft.Text(msg))
                page.snack_bar.open = True
            
            page.update()
            
        except Exception as e:
            page.clean()
            page.add(ft.Text(f"主页渲染失败: {e}", color="red"))
            page.update()

    def render_add_page(e=None):
        page.clean()
        page.floating_action_button = None
        
        name_field = ft.TextField(label="任务名称", autofocus=False)
        days_field = ft.TextField(label="天数 (数字)", keyboard_type="number")

        def on_confirm(e):
            if not name_field.value or not days_field.value:
                return
            e.control.text = "保存中..."
            e.control.update()
            do_add_task(name_field.value, days_field.value)

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
                        ft.Container(height=40),
                        ft.Row([
                            ft.ElevatedButton("取消", on_click=on_cancel),
                            ft.ElevatedButton("创建", on_click=on_confirm, bgcolor="teal", color="white"),
                        ], alignment="center")
                    ], horizontal_alignment="center")
                )
            )
        )
        page.update()

    render_main_page()

if __name__ == "__main__":
    ft.app(target=main)
