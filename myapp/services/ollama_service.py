import json
import requests
import re
import logging


class OllamaService:
    def __init__(self):
        self.api_url = "http://localhost:11434/api/generate"
        self.model = "gemma3"

        # ตั้งค่า logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        if not self.logger.hasHandlers():
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def clean_json_text(self, text):
        """
        พยายามแยกข้อความ JSON ออกมาจากข้อความที่ส่งกลับ
        """
        # วิธีที่ 1: หา JSON ที่ล้อมรอบด้วย ```json
        if "```json" in text:
            match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
            if match:
                return match.group(1).strip()

        # วิธีที่ 2: หา JSON ที่ล้อมรอบด้วย ```
        if "```" in text:
            match = re.search(r"```\s*([\s\S]*?)\s*```", text)
            if match:
                return match.group(1).strip()

        # วิธีที่ 3: หา JSON ระหว่างวงเล็บปีกกา
        match = re.search(r"(\{[\s\S]*\})", text)
        if match:
            return match.group(1).strip()

        # ถ้าไม่พบ JSON ให้ตรวจสอบส่วนหลังของข้อความ
        parts = text.split('\n')
        for part in reversed(parts):
            part = part.strip()
            if part.startswith('{') and part.endswith('}'):
                return part

        # ถ้าไม่สามารถแยก JSON ได้ ส่งคืนข้อความเดิม
        return text.strip()

    def fix_json(self, text):
        """
        พยายามแก้ไข JSON ที่ไม่ถูกต้อง
        """
        # แก้ไขปัญหา single quotes แทน double quotes
        text = re.sub(r"'([^']*)':\s*", r'"\1": ', text)
        text = re.sub(r":\s*'([^']*)'", r': "\1"', text)

        # แก้ไขปัญหา trailing commas
        text = re.sub(r",\s*}", "}", text)
        text = re.sub(r",\s*\]", "]", text)

        # แก้ไขปัญหา comments
        text = re.sub(r"//.*?\n", "\n", text)

        # เพิ่มการจัดการกรณี JSON ที่ไม่สมบูรณ์
        text = text.replace('\n', '').replace('\r', '')

        return text

    def generate_matchmaking(self, room_data):
        text = ""
        debug_info = {}

        try:
            # สำหรับ Gemma3 อาจต้องปรับ prompt ให้ชัดเจนขึ้น
            system_prompt = """คุณเป็นผู้เชี่ยวชาญการจัดการแข่งขันแบดมินตัน โปรดตอบกลับในรูปแบบ JSON ที่ถูกต้อง"""

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

            skill_levels = [p['skill'] for p in player_list]
            skill_summary = ", ".join([f"{skill}: {skill_levels.count(skill)} คน" for skill in set(skill_levels)])

            user_prompt = f"""จงจัดทีมแบดมินตันให้สมดุลที่สุด:

            กฎการจัดทีม:
            1. กระจายผู้เล่นทักษะต่างๆ อย่างเท่าเทียม
            2. คำนึงถึงจำนวนแมตช์และเวลาที่เข้าร่วม
            
            รายชื่อผู้เล่น:
            {player_info}
            
            
            ตอบกลับเป็น JSON เท่านั้น ดังโครงสร้าง:
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
            }}"""

            # สำหรับ Gemma3 อาจใช้ prompt แบบง่ายขึ้น
            payload = {
                "model": self.model,
                "prompt": user_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "top_p": 0.9,
                    "num_predict": 1024
                }
            }

            self.logger.info(f"Sending request to Ollama API for model: {self.model}")
            response = requests.post(self.api_url, json=payload)

            if response.status_code != 200:
                self.logger.error(f"API request failed with status {response.status_code}: {response.text}")
                raise Exception(f"API request failed with status {response.status_code}: {response.text}")

            # Ollama API จะตอบกลับในรูปแบบ {"response": "text response here"}
            text = response.json().get("response", "")
            debug_info["raw_response"] = text[:200] + "..." if len(text) > 200 else text

            # ทำความสะอาดเพื่อให้ได้ JSON ที่ถูกต้อง
            json_text = self.clean_json_text(text)
            debug_info["cleaned_json"] = json_text[:200] + "..." if len(json_text) > 200 else json_text

            # ถ้ายังไม่สามารถแปลงเป็น JSON ได้ ลองแก้ไข JSON
            try:
                matchmaking_data = json.loads(json_text)
            except json.JSONDecodeError:
                # สำหรับ Gemma3 อาจต้องมีการแก้ไข JSON ที่ละเอียดมากขึ้น
                fixed_json = self.fix_json(json_text)
                debug_info["fixed_json"] = fixed_json[:200] + "..." if len(fixed_json) > 200 else fixed_json

                try:
                    matchmaking_data = json.loads(fixed_json)
                except json.JSONDecodeError:
                    # หากยังไม่สำเร็จ ลองดึง JSON ที่สมบูรณ์ที่สุด
                    alt_json = re.findall(r'\{.*\}', fixed_json, re.DOTALL)
                    if alt_json:
                        matchmaking_data = json.loads(alt_json[0])
                    else:
                        raise

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
            self.logger.error(f"JSON decode error: {str(e)}")
            return {
                "error": f"Could not parse AI response as JSON: {str(e)}",
                "raw_response": text[:1000] if 'text' in locals() and text else "No response",
                "debug_info": debug_info,
                "model_used": self.model
            }
        except Exception as e:
            self.logger.error(f"Error in generate_matchmaking: {str(e)}")
            return {
                "error": str(e),
                "debug_info": debug_info,
                "model_used": self.model
            }