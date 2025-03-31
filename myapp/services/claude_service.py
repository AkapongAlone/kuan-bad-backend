import os
import json
from anthropic import Anthropic

class ClaudeService:
    def __init__(self):
        self.client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.model = "claude-3-5-sonnet-20240620"

    def generate_matchmaking(self, room_data):

        system_prompt = """คุณเป็นผู้เชี่ยวชาญการจัดการแข่งขันแบดมินตัน และการจับคู่แมชต์การแข่งขันตามทักษะที่เหมาะสมกับรายชื่อนักกีฬาแต่ละคน
        คุณต้องตอบกลับในรูปแบบ JSON ที่มีโครงสร้างตามที่กำหนดเท่านั้น"""

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

        user_prompt = f"""
        จากรายชื่อผู้เล่นต่อไปนี้:

        {player_info}

        กรุณาจับคู่ผู้เล่นสำหรับการแข่งขันแบบคู่ (doubles) ที่มีความสมดุลที่สุด
        โดยพิจารณาจากระดับทักษะของผู้เล่น
        กฎการเลือกผู้เล่น:
        1.เลือกมา4คน โดยความสามารถใกล้เคียงกันคนเก่งที่สุดกับคนอ่อนที่สุดทักษะจะต่างกันไม่เกิน1 ขั้น หรือ ทักษะจะเท่ากันหมดทั้ง 4 คนเลยก็ได้
        2.ไม่ต้องสนใจเพศ วิเคราะห์จากจำนวนแมชต์ที่เล่น เทียบกับคนทั้งห้อง
        3.ประเมินในส่วนของเวลา ให้เทียบเวลาที่ผู้เล่น join เข้ามา ทุกๆ 30 นาทีเขาควรได้อย่างน้อยเล่น 1 match
        
        เมื่อเลือกผู้เล่นที่จะจัดทีมมาได้ 4 คนแล้ว ต่อไปคือกฎการจัดทีม
        
        กฎการจัดทีม:
        1.จับคู่ให้ทั้งสองทีมมีความสมดุลกัน โดยเน้นจากทักษะของผู้เล่นที่เลือกมา
                
                ตัวอย่างที่ถูกต้อง: 
                - ถ้ามีผู้เล่น 4 คน โดยเป็นระดับ S 2 คน และ P- 2 คน ควรจับให้แต่ละทีมมี S 1 คน และ P- 1 คน
                - ถ้ามีผู้เล่น 4 คน โดยเป็นระดับ N 1 คน, S 2 คน และ P- 1 คน ควรจับให้ทีมหนึ่งมี P- กับ N อีกทีมมี S กับ S เนื่องจาก P- เก่งกว่า S และ S เก่งกว่า N จัดแบบนี้จึงเหมาะสม
                
                ตัวอย่างที่ไม่ถูกต้อง:
                - จับให้ผู้เล่นระดับเดียวกัน อยู่ในทีมเดียวกัน เจอผู้เล่นคนละระดับอยู่ทีมตรงข้ามทั้งหมด
                
        ทักษะจะมีการจัดประเภทดังนี้:
        BG: ทักษะต่ำสุด พอตีลูกโดนบ้าง แทบไม่มีพื้นฐานการตี
        N: ตีลูกโดนบ่อยขึ้น แต่อาจจะไม่ 100% เมื่อตีลูกยากๆ และเล่นลูกที่ใช้ทักษะสูงๆได้ไม่ดีมากเช่น backhand, การวิ่ง, ลูกตบ
        S: ตีลูกโดน มีความชัวร์ในการตี มีเบสิคตีลุกต่างๆได้ครบ แต่ถ้าทางการตีอาจจะไม่สวยเท่าคนที่เรียนมา ส่วนใหญ่คนพวกนี้คือคนที่เล่นมานาน
        P-: เก่งกว่า S และอาจเคยเรียนมาก่อน มีแรงและความไวที่มากขึ้น ถึงแม้ท่าทางอาจไม่สวย แต่ลูกที่ตีออกไปมักค่อนข้างมีประสิทธิภาพ
        P/P+: มีทักษะระดับเป็นนักกีฬาเก่า หรือเป็นโค้ชสอนแบด มีเบสิค แรง ความเร็ว ครบถ้วน
        C: เป็นนักกีฬาหรือเคยเป็นนักกีฬาอาชีพ มีทักษะสูงมากๆ
        B/A: เป็นทีมชาติหรืออดีตทีมชาติ


        เลือกคน 2 คู่ เพื่อมาแข่งขันกัน และตอบกลับเป็น JSON ที่มีโครงสร้างดังนี้เท่านั้น:
        {{
          "teams": [
            {{
              "team_name": "ชื่อทีม 1",
              "players": [
                {{ "id": player_id, "name": "player_name", "skill": "skill_level" }},
                {{ "id": player_id, "name": "player_name", "skill": "skill_level" }}
              ],
              "compatibility_score": 85 // คะแนนความเข้ากันของคู่นี้ (0-100)
            }},
            {{
              "team_name": "ชื่อทีม 2",
              "players": [
                {{ "id": player_id, "name": "player_name", "skill": "skill_level" }},
                {{ "id": player_id, "name": "player_name", "skill": "skill_level" }}
              ],
              "compatibility_score": 82
            }}
          ],
          "match": {{
            "team1": "ชื่อทีม 1",
            "team2": "ชื่อทีม 2",
            "balance_score": 90,  // คะแนนความสมดุลของการแข่งขัน (0-100)
          }},
          "analysis": "คำอธิบายการจับคู่และเหตุผล รวมถึงข้อแนะนำอื่นๆ"
        }}

        ห้ามมีข้อความอื่นๆ นอกเหนือจาก JSON ที่กำหนด ชื่อทีมให้กำหนดเป็น ทีมที่ 1 กับ ทีมที่ 2 เท่านั้น analysis ให้ตอบเป็นภาษาไทยเท่านั้น
        """

        response = None

        try:
            response = self.client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )

            # แปลงข้อความตอบกลับเป็น JSON
            result_text = response.content[0].text.strip()

            # ลบเครื่องหมาย ``` ออกถ้ามี (กรณีที่ Claude ตอบกลับเป็น code block)
            if result_text.startswith('```json'):
                result_text = result_text.replace('```json', '', 1)
                if result_text.endswith('```'):
                    result_text = result_text[:-3]
            elif result_text.startswith('```'):
                result_text = result_text.replace('```', '', 1)
                if result_text.endswith('```'):
                    result_text = result_text[:-3]

            result_text = result_text.strip()

            # แปลง JSON string เป็น Python dictionary
            matchmaking_data = json.loads(result_text)

            # ปรับโครงสร้าง response ให้รองรับการแสดงผลที่ต้องการ
            return {
                "teams": matchmaking_data.get("teams", []),
                "match": matchmaking_data.get("match", {}),
                "analysis": matchmaking_data.get("analysis", ""),
                "model_used": self.model
            }

        except json.JSONDecodeError as e:
            # กรณีที่ AI ไม่ได้ตอบกลับในรูปแบบ JSON ที่ถูกต้อง
            error_data = {
                "error": "Could not parse AI response as JSON",
                "model_used": self.model
            }

            # เพิ่ม raw_response เฉพาะเมื่อ response มีค่า
            if response:
                error_data["raw_response"] = response.content[0].text

            return error_data
        except Exception as e:
            # จัดการ error อื่นๆ
            return {
                "error": str(e),
                "model_used": self.model
            }


