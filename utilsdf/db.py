import datetime
import sqlite3
import random
import string
from typing import Union, Optional, Dict
from os import getenv


class Database:
    _instance = None
    BOT_TABLE = "bot"
    BOT_KEYS_TABLE = "bot_keys"
    BOT_GROUPS = "groups"
    ID_OWNER = '7450372939'

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance.connection = sqlite3.connect("assets/db_bot.db")
            cls._instance.cursor = cls._instance.connection.cursor()
            cls._instance.__create_tables()
            cls._instance.__initialize_owner()
        return cls._instance

    def __create_tables(self) -> None:
        table_defs = {
            self.BOT_TABLE: [
                ("ID", "VARCHAR(25) NOT NULL PRIMARY KEY"),
                ("USERNAME", "VARCHAR(32) DEFAULT NULL UNIQUE"),
                ("NICK", "VARCHAR(32) DEFAULT '¿?'"),
                ("RANK", "VARCHAR(15) DEFAULT 'user'"),
                ("STATE", "VARCHAR(12) DEFAULT 'free'"),
                ("MEMBERSHIP", "VARCHAR(15) DEFAULT 'free user'"),
                ("EXPIRATION", "varchar(20) DEFAULT NULL"),
                ("ANTISPAM", "INT(3) DEFAULT 60"),
                ("CREDITS", "INT(15) DEFAULT 0"),
                ("REGISTERED", "TEXT NOT NULL"),
                ("CHECKS", "INT(15) DEFAULT 0"),
            ],
            self.BOT_KEYS_TABLE: [
                ("BOT_KEY", "VARCHAR(30) NOT NULL PRIMARY KEY"),
                ("EXPIRATION", "TEXT NOT NULL"),
            ],
            self.BOT_GROUPS: [
                ("ID", "VARCHAR(30) NOT NULL PRIMARY KEY"),
                ("EXPIRATION", "TEXT NOT NULL"),
                ("PROVIDER", "VARCHAR(30) NOT NULL"),
            ],
        }

        for table, columns in table_defs.items():
            self.__create_table(table, columns)

        self.connection.commit()

    def __create_table(self, table_name: str, columns: list) -> None:
        column_defs = ", ".join(f"{name} {defn}" for name, defn in columns)
        query = f"CREATE TABLE IF NOT EXISTS {table_name}({column_defs})"
        self.cursor.execute(query)

    def __initialize_owner(self) -> None:
        if not self.is_seller_or_admin(self.ID_OWNER):
            self.promote_to_admin(self.ID_OWNER)
            self.add_premium_membership(self.ID_OWNER, 30, 300)

    def add_premium_membership(
        self, user_id: int, days: int, credits: int
    ) -> Optional[str]:
        user_id, days, credits = map(int, (user_id, days, credits))
        user_data = self.cursor.execute(
            f"SELECT MEMBERSHIP FROM {self.BOT_TABLE} WHERE ID=?", (user_id,)
        ).fetchone()

        if user_data is None:
            return None

        expiration_time = (
            datetime.datetime.now() + datetime.timedelta(days=days)
        ).strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute(
            f"UPDATE {self.BOT_TABLE} SET MEMBERSHIP='Premium', ANTISPAM=40, CREDITS=?, EXPIRATION=? WHERE ID=?",
            (credits, expiration_time, user_id),
        )
        self.connection.commit()
        return expiration_time

    def is_premium(self, user_id: int) -> bool:
        user_data = self.cursor.execute(
            f"SELECT MEMBERSHIP FROM {self.BOT_TABLE} WHERE ID=?", (user_id,)
        ).fetchone()
        return str(user_data[0]).lower() == "premium" if user_data else False

    def register_user(self, user_id: int, username: str) -> None:
        try:
            user_id = int(user_id)
            time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                f"INSERT INTO {self.BOT_TABLE} (ID, USERNAME, REGISTERED) VALUES (?, ?, ?)",
                (user_id, username, time),
            )
            self.connection.commit()
        except sqlite3.IntegrityError:
            pass

    def gen_key(self, days: int) -> tuple:
        expire_day = (
            datetime.datetime.now() + datetime.timedelta(days=int(days))
        ).strftime("%Y-%m-%d %H:%M:%S")
        key = "key-aktz" + "".join(
            random.choice(string.ascii_letters) for _ in range(8)
        )
        self.cursor.execute(
            f"INSERT INTO {self.BOT_KEYS_TABLE} (BOT_KEY, EXPIRATION) VALUES (?, ?)",
            (key, expire_day),
        )
        self.connection.commit()
        return key, expire_day

    def rename_premium(self, user_id: int) -> Optional[int]:
        user_id = int(user_id)
        user_data = self.cursor.execute(
            f"SELECT MEMBERSHIP FROM {self.BOT_TABLE} WHERE ID=?", (user_id,)
        ).fetchone()
        if user_data is None:
            return None

        self.cursor.execute(
            f"UPDATE {self.BOT_TABLE} SET MEMBERSHIP='free user', RANK='user', ANTISPAM=60, EXPIRATION=NULL WHERE ID=?",
            (user_id,),
        )
        self.connection.commit()
        return 1

    def remove_group(self, chat_id: str) -> Optional[int]:
        data = self.cursor.execute(
            f"SELECT EXPIRATION FROM {self.BOT_GROUPS} WHERE ID=?",
            (chat_id,),
        ).fetchone()
        if data is None:
            return None

        self.cursor.execute(
            f"DELETE FROM {self.BOT_GROUPS} WHERE ID=?",
            (chat_id,),
        )
        self.connection.commit()
        return 1

    def unban_or_ban_user(self, user_id: int, ban: bool = True) -> Optional[int]:
        user_id = int(user_id)
        user_data = self.cursor.execute(
            f"SELECT MEMBERSHIP FROM {self.BOT_TABLE} WHERE ID=?", (user_id,)
        ).fetchone()
        if user_data is None:
            return None
        status = "ban" if ban else "free"

        self.cursor.execute(
            f"UPDATE {self.BOT_TABLE} SET RANK='user', MEMBERSHIP='free user', ANTISPAM=60, CREDITS=0, EXPIRATION=NULL, STATE=? WHERE ID=?",
            (status, user_id),
        )
        self.connection.commit()
        return 1

    def is_ban(self, user_id: int) -> bool:
        user_id = int(user_id)
        user_data = self.cursor.execute(
            f"SELECT STATE FROM {self.BOT_TABLE} WHERE ID=?", (user_id,)
        ).fetchone()
        return str(user_data[0]).lower() == "ban" if user_data else False

    def claim_key(self, key: str, user_id: int) -> Optional[str]:
        data = self.cursor.execute(
            f"SELECT EXPIRATION FROM {self.BOT_KEYS_TABLE} WHERE BOT_KEY=?",
            (key,),
        ).fetchone()
        if data is None:
            return None
        expiration_time = data[0]
        self.cursor.execute(
            f"UPDATE {self.BOT_TABLE} SET MEMBERSHIP='Premium', ANTISPAM=40, EXPIRATION=? WHERE ID=?",
            (expiration_time, user_id),
        )
        self.cursor.execute(
            f"DELETE FROM {self.BOT_KEYS_TABLE} WHERE BOT_KEY=?", (key,)
        )
        self.connection.commit()
        return expiration_time

    def __is_rank(self, user_id: int, rank: str) -> bool:
        user_id = int(user_id)
        user_data = self.cursor.execute(
            f"SELECT RANK FROM {self.BOT_TABLE} WHERE ID=?", (user_id,)
        ).fetchone()
        return str(user_data[0]).lower() == rank if user_data else False

    def is_admin(self, user_id: int) -> bool:
        return self.__is_rank(user_id, "admin")

    def is_seller(self, user_id: int) -> bool:
        return self.__is_rank(user_id, "seller")

    def is_seller_or_admin(self, user_id) -> bool:
        if self.is_admin(user_id) or self.is_seller(user_id):
            return True
        return False

    def __get_info(self, ID: int, group: bool = False) -> list:
        ID = int(ID)
        table = self.BOT_GROUPS if group else self.BOT_TABLE
        data = self.cursor.execute(f"SELECT * FROM {table} WHERE ID=?", (ID,))
        data = data.fetchone()
        return data

    def get_info_user(self, user_id: int) -> Dict[str, Union[str, int]] | None:
        user_data = self.__get_info(user_id)
        return (
            {
                "ID": user_data[0],
                "USERNAME": user_data[1],
                "NICK": user_data[2],
                "RANK": user_data[3],
                "STATE": user_data[4],
                "MEMBERSHIP": user_data[5],
                "EXPIRATION": user_data[6],
                "ANTISPAM": user_data[7],
                "CREDITS": user_data[8],
                "REGISTERED": user_data[9],
                "CHECKS": user_data[10],
            }
            if user_data
            else None
        )

    def get_info_group(self, chat_id: int) -> Dict[str, Union[str, int]] | None:
        group_data = self.__get_info(chat_id, True)
        if not group_data:
            return None
        return {
            "ID": group_data[0],
            "EXPIRATION": group_data[1],
        }

    def get_chats_ids(self) -> list:
        users_data = self.cursor.execute(f"SELECT ID FROM {self.BOT_TABLE}")
        users_data = users_data.fetchall()
        chats_id_data = self.cursor.execute(f"SELECT ID FROM {self.BOT_GROUPS}")
        users_data.extend(chats_id_data.fetchall())
        return [data[0] for data in users_data]

    def group_authorized(self, chat_id: int) -> bool:
        chat_id = int(chat_id)
        data = self.cursor.execute(
            f"SELECT EXPIRATION FROM {self.BOT_GROUPS} WHERE ID=?",
            (chat_id,),
        ).fetchone()
        expiration = data
        if expiration is None:
            return False
        return True

    def user_has_credits(self, user_id: int) -> bool:
        credits_user = self.cursor.execute(
            f"SELECT CREDITS FROM {self.BOT_TABLE} WHERE ID=?",
            (user_id,),
        ).fetchone()[0]
        return credits_user > 0

    def remove_credits(self, user_id: int, credits: int) -> None:
        if credits <= 0:
            return
        credits_user = self.cursor.execute(
            f"SELECT CREDITS FROM {self.BOT_TABLE} WHERE ID=?",
            (user_id,),
        ).fetchone()[0]
        new_credits = credits_user - credits if credits_user > 0 else 0
        self.cursor.execute(
            f"UPDATE {self.BOT_TABLE} SET CREDITS=? WHERE ID=?",
            (new_credits, user_id),
        )
        self.connection.commit()

    def add_group(self, chat_id: int, days: int, username: str) -> Union[str, bool]:
        try:
            chat_id = int(chat_id)
            expiration_time = (
                datetime.datetime.now() + datetime.timedelta(days=days)
            ).strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                f"INSERT INTO {self.BOT_GROUPS} (ID, EXPIRATION, PROVIDER) VALUES (?, ?, ?)",
                (chat_id, expiration_time, username),
            )
            self.connection.commit()
        except sqlite3.IntegrityError:
            self.cursor.execute(
                f"UPDATE {self.BOT_GROUPS} SET EXPIRATION=?, PROVIDER=? WHERE ID=?",
                (expiration_time, username, chat_id),
            )
            self.connection.commit()
        return expiration_time

    def is_authorized(self, user_id: int, chat_id: int) -> bool:
        user_id = int(user_id)
        chat_id = int(chat_id)

        if self.is_premium(user_id) or self.group_authorized(chat_id):
            return True
        return False

    def remove_expireds_users(self) -> None:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        table_queries = [
            {"table": self.BOT_TABLE, "remove_function": self.rename_premium},
            {"table": self.BOT_GROUPS, "remove_function": self.remove_group},
        ]

        for query_data in table_queries:
            query_format = f"SELECT ID, EXPIRATION FROM {query_data['table']} WHERE EXPIRATION IS NOT NULL"
            data = self.cursor.execute(query_format)
            expireds = filter(lambda x: x[1] < now, data.fetchall())

            for data_item in expireds:
                query_data["remove_function"](data_item[0])

    def increase_checks(self, user_id: int, quantity: int = 1) -> bool | None:
        user_id, quantity = map(int, (user_id, quantity))

        user_data = self.cursor.execute(
            f"SELECT CHECKS FROM {self.BOT_TABLE} WHERE ID=?", (user_id,)
        ).fetchone()

        if user_data is None:
            return None

        checks = user_data[0] + quantity
        self.cursor.execute(
            f"UPDATE {self.BOT_TABLE} SET CHECKS=? WHERE ID=?",
            (checks, user_id),
        )
        self.connection.commit()
        return True

    def update_colum(self, user_id: int, column: str, value) -> bool | None:
        user_id = int(user_id)

        user_data = self.cursor.execute(
            f"SELECT USERNAME FROM {self.BOT_TABLE} WHERE ID=?", (user_id,)
        ).fetchone()

        if user_data is None:
            return None

        self.cursor.execute(
            f"UPDATE {self.BOT_TABLE} SET {column}=? WHERE ID=?",
            (value, user_id),
        )
        self.connection.commit()
        return True

    def __promote(self, user_id: int, rank: str) -> bool | None:
        user_id = int(user_id)
        user_data = self.cursor.execute(
            f"SELECT RANK FROM {self.BOT_TABLE} WHERE ID=?", (user_id,)
        ).fetchone()

        if user_data is None:
            return None

        self.cursor.execute(
            f"UPDATE {self.BOT_TABLE} SET RANK=? WHERE ID=?",
            (rank, user_id),
        )
        self.connection.commit()
        return True

    def set_nick(self, user_id: int, nick: str) -> bool | None:
        user_id = int(user_id)

        user_data = self.cursor.execute(
            f"SELECT NICK FROM {self.BOT_TABLE} WHERE ID=?", (user_id,)
        ).fetchone()

        if user_data is None:
            return None

        self.cursor.execute(
            f"UPDATE {self.BOT_TABLE} SET NICK=? WHERE ID=?",
            (nick, user_id),
        )
        self.connection.commit()
        return True

    def set_antispam(self, user_id: int, antispam: int) -> bool | None:
        user_id, antispam = map(int, (user_id, antispam))

        user_data = self.cursor.execute(
            f"SELECT ANTISPAM FROM {self.BOT_TABLE} WHERE ID=?", (user_id,)
        ).fetchone()

        if user_data is None:
            return None

        self.cursor.execute(
            f"UPDATE {self.BOT_TABLE} SET ANTISPAM=? WHERE ID=?",
            (antispam, user_id),
        )
        self.connection.commit()
        return True

    def promote_to_seller(self, user_id: int) -> bool | None:
        return self.__promote(user_id, "seller")

    def promote_to_admin(self, user_id: int) -> bool | None:
        return self.__promote(user_id, "admin")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.connection.commit()
