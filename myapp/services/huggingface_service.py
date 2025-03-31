# services/huggingface_service.py
import os
import json
import requests
import re
from dotenv import load_dotenv

load_dotenv()


class HuggingFaceService:
    def __init__(self):
        # ใช้ API key จาก environment variable
        self.api_key = os.environ.get("HUGGINGFACE_API_KEY", "")
        # Mistral 7B Instruct เป็นโมเดลที่ดีและมีประสิทธิภาพสูง
        self.model = "mistralai/Mistral-7B-Instruct-v0.2"
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model}"
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def clean_json_text(self, text):
        """
        ฟังก์ชันทำความสะอาดข้อความให้เป็น JSON ที่ถูกต้อง
        """
        # ลองหลายวิธีในการแยก JSON ออกมา

        # วิธีที่ 1: หา JSON ระหว่าง ``` blocks (มักใช้ใน markdown)
        if "```json" in text:
            match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
            if match:
                return match.group(1).strip()

        # วิธีที่ 2: หา JSON ระหว่าง ``` blocks โดยไม่ระบุภาษา
        if "```" in text:
            match = re.search(r"```\s*([\s\S]*?)\s*```", text)
            if match:
                return match.group(1).strip()

        # วิธีที่ 3: หา JSON จากวงเล็บปีกกาแรกถึงวงเล็บปีกกาสุดท้าย
        match = re.search(r"(\{[\s\S]*\})", text)
        if match:
            return match.group(1).strip()

        # ถ้าไม่สามารถแยก JSON ได้ ส่งคืนข้อความเดิม
        return text.strip()

    def fix_json(self, text):
        """
        พยายามแก้ไข JSON ที่ไม่ถูกต้อง
        """
        # แก้ไขปัญหา single quotes แทน double quotes
        text = re.sub(r"'([^']*)':\s*", r'"\1": ', text)
        text = re.sub(r":\s*'([^']*)'", r': "\1"', text)

        # แก้ไขปัญหา trailing commas ใน arrays และ objects
        text = re.sub(r",\s*}", "}", text)
        text = re.sub(r",\s*\]", "]", text)

        # แก้ไขปัญหา comments ใน JSON
        text = re.sub(r"//.*?\n", "\n", text)

        return text

    def generate_matchmaking(self, room_data):
        text = ""
        debug_info = {}

        try:
            system_prompt = """คุณเป็นผู้เชี่ยวชาญการจัดการแข่งขันแบดมินตัน และการจับคู่แมชต์การแข่งขันตามทักษะที่เหมาะสมกับรายชื่อนักกีฬาแต่ละคน
            คุณต้องตอบกลับในรูปแบบ JSON ที่มีโครงสร้างตามที่กำหนดเท่านั้น และต้องตอบเป็นภาษาไทยทั้งหมด"""

            player_list = []
            for p in room_data['players']:
                player_list.append({
                    'id': p['id'],
                    'name': p['name'],
                    'skill': p['skill'],
                    'join_time': p.get('join_time', ''),
                    'number_of_matches': p.get('number_of_matches', 0),
                    'number_of_shuttlecock': p.get('number_of_shuttlecock', 0)
                })

            player_info = "\n".join([
                f"Player {p['id']}: {p['name']} (Skill: {p['skill']}, Matches: {p['number_of_matches']}, Join Time: {p['join_time']})"
                for p in player_list
            ])

            # จัดทำรายการระดับทักษะที่มีอยู่ในห้อง
            skill_levels = [p['skill'] for p in player_list]
            skill_summary = ", ".join([f"{skill}: {skill_levels.count(skill)} คน" for skill in set(skill_levels)])

            user_prompt = f"""
                จากรายชื่อผู้เล่นต่อไปนี้:
                
                {player_info}
                                
                กรุณาจับคู่ผู้เล่นสำหรับการแข่งขันแบบคู่ (doubles) ที่มีความสมดุลที่สุด โดยมีกฎเกณฑ์ดังนี้:
                
                กฎข้อที่ 1 (สำคัญที่สุด): จับคู่ให้ทั้งสองทีมมีความสมดุลกัน โดยเน้นจากทักษะของผู้เล่นที่เลือกมา
                
                ตัวอย่างที่ถูกต้อง: 
                - ถ้ามีผู้เล่น 4 คน โดยเป็นระดับ S 2 คน และ P- 2 คน ควรจับให้แต่ละทีมมี S 1 คน และ P- 1 คน
                - ถ้ามีผู้เล่น 4 คน โดยเป็นระดับ N 1 คน, S 2 คน และ P- 1 คน ควรจับให้ทีมหนึ่งมี P- กับ N อีกทีมมี S กับ S เนื่องจาก P- เก่งกว่า S และ S เก่งกว่า N จัดแบบนี้จึงเหมาะสม
                
                ตัวอย่างที่ไม่ถูกต้อง:
                - จับให้ผู้เล่นระดับเดียวกัน อยู่ในทีมเดียวกัน เจอผู้เล่นคนละระดับอยู่ทีมตรงข้ามทั้งหมด
                
                กฎข้อที่ 2: พิจารณาจำนวนแมชต์ที่เล่น เทียบกับคนทั้งห้อง
                กฎข้อที่ 3: พิจารณาเวลาที่ผู้เล่น join เข้ามา ทุกๆ 30 นาทีเขาควรได้อย่างน้อยเล่น 1 match
                
                ทักษะจะมีการจัดประเภทดังนี้(เรียงลำดับความเก่งจากน้อยไปมาก):
                1. BG: อ่อนที่สุด ทักษะต่ำสุด พอตีลูกโดนบ้าง แทบไม่มีพื้นฐานการตี
                2. N: เก่งกว่า BG ตีลูกโดนบ่อยขึ้น แต่อาจจะไม่ 100% เมื่อตีลูกยากๆ และเล่นลูกที่ใช้ทักษะสูงๆได้ไม่ดีมากเช่น backhand, การวิ่ง, ลูกตบ
                3. S: เก่งกว่า N ตีลูกโดน มีความชัวร์ในการตี มีเบสิคตีลุกต่างๆได้ครบ แต่ถ้าทางการตีอาจจะไม่สวยเท่าคนที่เรียนมา ส่วนใหญ่คนพวกนี้คือคนที่เล่นมานาน
                4. P-: เก่งกว่า S และอาจเคยเรียนมาก่อน มีแรงและความไวที่มากขึ้น ถึงแม้ท่าทางอาจไม่สวย แต่ลูกที่ตีออกไปมักค่อนข้างมีประสิทธิภาพ
                5. P/P+: เก่งกว่า P- มีทักษะระดับเป็นนักกีฬาเก่า หรือเป็นโค้ชสอนแบด มีเบสิค แรง ความเร็ว ครบถ้วน
                6. C: เก่งกว่าP/P+ เป็นนักกีฬาหรือเคยเป็นนักกีฬาอาชีพ มีทักษะสูงมากๆ
                7. B/A: เก่งที่สุด เป็นทีมชาติหรืออดีตทีมชาติ
                
                ในการจัดแมชต์ทักษะไม่จำเป็นต้องเท่ากัน แต่ก็ไม่ควรห่างกันเกิน 1 ขั้น
                
                คุณจะต้องตอบกลับเป็น JSON ที่มีโครงสร้างดังนี้เท่านั้น:
                {{
                  "teams": [
                    {{
                      "team_name": "ทีมที่ 1",
                      "players": [
                        {{ "id": player_id, "name": "player_name", "skill": "skill_level" }},
                        {{ "id": player_id, "name": "player_name", "skill": "skill_level" }}
                      ],
                      "compatibility_score": 85
                    }},
                    {{
                      "team_name": "ทีมที่ 2",
                      "players": [
                        {{ "id": player_id, "name": "player_name", "skill": "skill_level" }},
                        {{ "id": player_id, "name": "player_name", "skill": "skill_level" }}
                      ],
                      "compatibility_score": 82
                    }}
                  ],
                  "match": {{
                    "team1": "ทีมที่ 1",
                    "team2": "ทีมที่ 2",
                    "balance_score": 90
                  }},
                  "analysis": "คำอธิบายการจับคู่และเหตุผล"
                }}
                
                คำแนะนำสำคัญ: ตอบเป็น JSON เท่านั้น ไม่ต้องมีข้อความอื่นๆ นอกเหนือจาก JSON คุณสามารถอธิบายเหตุผลของการจับคู่ในฟิลด์ "analysis" ได้ ต้องใช้ภาษาไทยในส่วน analysis ครอบคลุมการจับคู่ว่าเลือกอย่างไร ทำไมถึงเลือกแบบนี้ และข้อแนะนำเพิ่มเติม ขอบคุณ
                
                ตัวอย่าง JSON ที่ถูกต้อง:
                {{
                  "teams": [
                    {{
                      "team_name": "ทีมที่ 1",
                      "players": [
                        {{ "id": 1, "name": "สมชาย", "skill": "S" }},
                        {{ "id": 3, "name": "สมศรี", "skill": "P-" }}
                      ],
                      "compatibility_score": 85
                    }},
                    {{
                      "team_name": "ทีมที่ 2",
                      "players": [
                        {{ "id": 2, "name": "สมหญิง", "skill": "S" }},
                        {{ "id": 4, "name": "สมปอง", "skill": "P-" }}
                      ],
                      "compatibility_score": 82
                    }}
                  ],
                  "match": {{
                    "team1": "ทีมที่ 1",
                    "team2": "ทีมที่ 2",
                    "balance_score": 90
                  }},
                  "analysis": "การจับคู่นี้เป็นการจับคู่ที่สมดุลที่สุด เพราะทั้งสองทีมมีผู้เล่นทักษะ S และ P- ทีมละ 1 คน ทำให้พละกำลังและความสามารถของทั้งสองทีมใกล้เคียงกันมาก"
                }}
                """
            # รวม system_prompt และ user_prompt ในรูปแบบที่ Mistral ต้องการ
            full_prompt = f"<s>[INST] {system_prompt}\n\n{user_prompt} [/INST]</s>"

            # เรียกใช้ Hugging Face API
            payload = {
                "inputs": full_prompt,
                "parameters": {
                    "max_new_tokens": 1024,
                    "temperature": 0.2,  # ลดค่า temperature ลงเพื่อให้ตอบตรงกับคำสั่งมากขึ้น
                    "top_p": 0.95,
                    "return_full_text": False
                }
            }

            response = None
            response = requests.post(self.api_url, headers=self.headers, json=payload)

            if response.status_code != 200:
                raise Exception(f"API request failed with status {response.status_code}: {response.text}")

            text = response.json()[0]["generated_text"]
            debug_info["raw_response"] = text[:200] + "..." if len(text) > 200 else text

            # ทำความสะอาดเพื่อให้ได้ JSON ที่ถูกต้อง
            json_text = self.clean_json_text(text)
            debug_info["cleaned_json"] = json_text[:200] + "..." if len(json_text) > 200 else json_text

            # ถ้ายังไม่สามารถแปลงเป็น JSON ได้ ลองแก้ไข JSON
            try:
                matchmaking_data = json.loads(json_text)
            except json.JSONDecodeError:
                fixed_json = self.fix_json(json_text)
                debug_info["fixed_json"] = fixed_json[:200] + "..." if len(fixed_json) > 200 else fixed_json
                matchmaking_data = json.loads(fixed_json)

            # ตรวจสอบว่า analysis เป็นภาษาไทยหรือไม่
            if "analysis" in matchmaking_data and matchmaking_data["analysis"]:
                # ตรวจสอบว่ามีตัวอักษรไทยอย่างน้อย 1 ตัว
                thai_chars = [c for c in matchmaking_data["analysis"] if '\u0e00' <= c <= '\u0e7f']
                if not thai_chars:
                    # ถ้าไม่พบตัวอักษรไทย ให้เพิ่มข้อความแจ้งเตือน
                    matchmaking_data["analysis"] = "ระบบไม่สามารถวิเคราะห์เป็นภาษาไทยได้ กรุณาตรวจสอบ prompt อีกครั้ง"

            result = {
                "teams": matchmaking_data.get("teams", []),
                "match": matchmaking_data.get("match", {}),
                "analysis": matchmaking_data.get("analysis", ""),
                "model_used": self.model
            }

            # ตรวจสอบว่ามีข้อมูลครบถ้วนหรือไม่
            if not result["teams"] or len(result["teams"]) < 2:
                raise Exception("ไม่พบข้อมูลทีมในผลลัพธ์")

            return result

        except json.JSONDecodeError as e:
            return {
                "error": f"Could not parse AI response as JSON: {str(e)}",
                "raw_response": text[:1000] if 'text' in locals() and text else "No response",
                "debug_info": debug_info,
                "model_used": self.model
            }
        except Exception as e:
            return {
                "error": str(e),
                "debug_info": debug_info,
                "model_used": self.model
            }