import flet as ft
from datetime import datetime
import os

# 注意：移动端不再需要 daka_data.json 文件，数据会自动存在手机内部

def main(page: ft.Page):
    # ================= 1. 基础配置 =================
    # 尝试加载字体 (电脑端为了预览，手机端通常会自动回退到默认或打包资源)
    # 为了打包方便，我们这里做个简单的容错
    font_name = "my_font"
    font_path = "msyh.ttc"
    if not os.path.exists(font_path):
        font_path = "msyh.ttf"
    
    if os.path.exists(font_path):
        page.fonts = {font_name: font_path}
        page.theme = ft.Theme(font_family=font_name)
    else:
        # 如果没找到字体文件（比如在手机上），使用系统默认，防止崩溃
        page.theme = ft.Theme()

    page.title = "逆序打卡 (手机版)"
    page.theme_mode = "light"
    page.scroll = "auto"
    
    # ================= 2. 数据处理 (核心修改：使用 ClientStorage) =================
    def load_data():
        # 从手机内部存储读取数据
        data = page.client_storage.get("daka_data")
        if data is None:
            return {"tasks": [], "achievements": []}
        return data

    def save_data(data):
        # 保存到手机内部存储
        page.client_storage.set("daka_data", data)

    # 加载数据
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
                else:
                    task['checked_today'] = True
                    task['last_interaction'] = datetime.now().strftime("%Y-%m-%d")
                
                save_data(app_data)
                render_main_page()
                break

    # 添加
    def do_add_task(name, days):
        if name and days:
            new_task = {
                "id": str(datetime.now().timestamp()),
                "name": name,
                "days": int(days),
                "original_target": int(days),
                "created_at": datetime.now().strftime("%Y-%m-%d"),
                "last_interaction": datetime.now().strftime("%Y-%m-%d"),
                "checked_today": False
            }
            app_data["tasks"].append(new_task)
            save_data(app_data)
        render_main_page()

    # ================= 4. UI 渲染 =================
    
    def render_main_page(e=None):
        page.clean()
        
        tasks_column = ft.Column(spacing=10)
        
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
                    height=80,
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
                                        ft.Text(str(task['days']), size=40, weight="bold", color=get_day_color(task['days'])),
                                        ft.Container(content=ft.Text("天", size=14, color="grey"), padding=ft.padding.only(top=12))
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER, spacing=2, tight=True
                                ),
                                alignment=ft.alignment.center,
                            ),
                            ft.Container(
                                content=ft.ElevatedButton(text=btn_text, disabled=is_done_today, bgcolor=btn_bg, color="white", width=80, style=ft.ButtonStyle(padding=5), on_click=on_click_checkin),
                                alignment=ft.alignment.center_right
                            )
                        ]
                    )
                )
            )
            tasks_column.controls.append(task_card)

        achievements_column = ft.Column(spacing=10)
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

        page.add(tabs)
        page.floating_action_button = ft.FloatingActionButton(icon="add", bgcolor="teal", on_click=render_add_page)
        page.update()

    def render_add_page(e=None):
        page.clean()
        page.floating_action_button = None
        name_field = ft.TextField(label="任务名称", autofocus=True)
        days_field = ft.TextField(label="目标天数", keyboard_type="number")

        def on_confirm(e):
            if name_field.value and days_field.value:
                do_add_task(name_field.value, days_field.value)
            else:
                name_field.error_text = "请输入内容"
                page.update()

        def on_cancel(e):
            render_main_page()

        page.add(
            ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Text("新建挑战", size=24, weight="bold"),
                    ft.Divider(),
                    ft.Container(height=20),
                    name_field,
                    days_field,
                    ft.Container(height=20),
                    ft.Row([
                        ft.ElevatedButton("取消", on_click=on_cancel, bgcolor="grey", color="white"),
                        ft.ElevatedButton("确定创建", on_click=on_confirm, bgcolor="teal", color="white"),
                    ], alignment="center")
                ])
            )
        )
        page.update()

    render_main_page()

if __name__ == "__main__":
    ft.app(target=main)