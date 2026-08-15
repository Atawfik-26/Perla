import customtkinter as ctk


class PerlaUI:

    def __init__(self, root, on_send):

        self.root = root
        self.on_send = on_send

        self.bg = "#0b0d0f"
        self.side = "#111318"
        self.panel = "#171a1f"
        self.text = "#f2f3f5"
        self.muted = "#858b95"
        self.user = "#242830"

        ctk.set_appearance_mode("dark")

        root.title("Perla")
        root.geometry("1100x700")
        root.minsize(850, 550)
        root.configure(fg_color=self.bg)

        self.build()


    def build(self):

        self.main = ctk.CTkFrame(
            self.root,
            fg_color=self.bg,
            corner_radius=0
        )
        self.main.pack(fill="both", expand=True)

        self.build_sidebar()
        self.build_chat()


    def build_sidebar(self):

        sidebar = ctk.CTkFrame(
            self.main,
            width=220,
            fg_color=self.side,
            corner_radius=0
        )
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        logo = ctk.CTkLabel(
            sidebar,
            text="✦  Perla",
            font=("Arial", 21, "bold"),
            text_color=self.text
        )
        logo.pack(
            anchor="w",
            padx=22,
            pady=(25, 30)
        )

        new = ctk.CTkButton(
            sidebar,
            text="+   محادثة جديدة",
            height=42,
            fg_color="#1b1e24",
            hover_color="#252931",
            corner_radius=10,
            anchor="w",
            command=self.new_chat
        )
        new.pack(fill="x", padx=14)

        label = ctk.CTkLabel(
            sidebar,
            text="المحادثات",
            font=("Arial", 11),
            text_color=self.muted
        )
        label.pack(
            anchor="w",
            padx=20,
            pady=(30, 10)
        )

        self.history = ctk.CTkScrollableFrame(
            sidebar,
            fg_color="transparent"
        )
        self.history.pack(
            fill="both",
            expand=True,
            padx=8
        )


    def build_chat(self):

        self.content = ctk.CTkFrame(
            self.main,
            fg_color=self.bg,
            corner_radius=0
        )
        self.content.pack(
            side="left",
            fill="both",
            expand=True
        )

        header = ctk.CTkFrame(
            self.content,
            height=58,
            fg_color=self.bg,
            corner_radius=0
        )
        header.pack(fill="x")
        header.pack_propagate(False)

        title = ctk.CTkLabel(
            header,
            text="بيرلا",
            font=("Arial", 15, "bold"),
            text_color=self.text
        )
        title.pack(side="left", padx=25)

        self.status = ctk.CTkLabel(
            header,
            text="جاهزة",
            font=("Arial", 10),
            text_color=self.muted
        )
        self.status.pack(side="right", padx=25)

        self.chat = ctk.CTkScrollableFrame(
            self.content,
            fg_color=self.bg,
            corner_radius=0
        )
        self.chat.pack(
            fill="both",
            expand=True,
            padx=55
        )

        self.show_welcome()
        self.build_input()


    def show_welcome(self):

        self.welcome = ctk.CTkFrame(
            self.chat,
            fg_color="transparent"
        )
        self.welcome.pack(pady=150)

        ctk.CTkLabel(
            self.welcome,
            text="✦",
            font=("Arial", 38),
            text_color="#ffffff"
        ).pack()

        ctk.CTkLabel(
            self.welcome,
            text="أهلاً أحمد",
            font=("Arial", 30, "bold"),
            text_color=self.text
        ).pack(pady=(10, 5))

        ctk.CTkLabel(
            self.welcome,
            text="أنا بيرلا، قولي عايز نبدأ في إيه؟",
            font=("Arial", 14),
            text_color=self.muted
        ).pack()


    def build_input(self):

        area = ctk.CTkFrame(
            self.content,
            fg_color=self.bg
        )
        area.pack(
            fill="x",
            padx=55,
            pady=(5, 20)
        )

        box = ctk.CTkFrame(
            area,
            height=58,
            fg_color=self.panel,
            corner_radius=18
        )
        box.pack(fill="x")

        self.entry = ctk.CTkEntry(
            box,
            height=52,
            fg_color="transparent",
            border_width=0,
            placeholder_text="اكتب لبيرلا...",
            text_color=self.text,
            placeholder_text_color="#666b74",
            font=("Arial", 14)
        )
        self.entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=18
        )

        send = ctk.CTkButton(
            box,
            text="↑",
            width=42,
            height=42,
            corner_radius=13,
            fg_color="#eeeeee",
            hover_color="#ffffff",
            text_color="#111111",
            font=("Arial", 20, "bold"),
            command=self.send
        )
        send.pack(side="right", padx=7)

        self.entry.bind(
            "<Return>",
            lambda event: self.send()
        )


    def send(self):

        message = self.entry.get().strip()

        if not message:
            return

        self.entry.delete(0, "end")
        self.on_send(message)


    def add_message(self, sender, message):

        if hasattr(self, "welcome"):

            if self.welcome.winfo_exists():
                self.welcome.destroy()

        row = ctk.CTkFrame(
            self.chat,
            fg_color="transparent"
        )
        row.pack(
            fill="x",
            pady=8
        )

        if sender == "user":

            label = ctk.CTkLabel(
                row,
                text=message,
                fg_color=self.user,
                corner_radius=15,
                text_color=self.text,
                font=("Arial", 14),
                wraplength=600,
                justify="left"
            )
            label.pack(
                side="right",
                padx=5
            )

        else:

            avatar = ctk.CTkLabel(
                row,
                text="✦",
                width=32,
                height=32,
                corner_radius=16,
                fg_color=self.panel,
                text_color=self.text,
                font=("Arial", 14)
            )
            avatar.pack(
                side="left",
                anchor="n",
                padx=(5, 10)
            )

            label = ctk.CTkLabel(
                row,
                text=message,
                fg_color="transparent",
                text_color=self.text,
                font=("Arial", 14),
                wraplength=700,
                justify="left"
            )
            label.pack(
                side="left",
                anchor="nw"
            )

        self.root.update_idletasks()
        self.chat._parent_canvas.yview_moveto(1.0)


    def set_status(self, text):

        self.status.configure(text=text)


    def add_history_item(self, text):

        button = ctk.CTkButton(
            self.history,
            text=text[:25],
            height=35,
            fg_color="transparent",
            hover_color="#1b1e24",
            text_color=self.muted,
            anchor="w"
        )
        button.pack(
            fill="x",
            pady=2
        )


    def new_chat(self):

        for widget in self.chat.winfo_children():
            widget.destroy()

        self.show_welcome()
        self.entry.focus()