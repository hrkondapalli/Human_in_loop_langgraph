from langgraph.graph import Graph
import os
os.environ["OPENAI_API_KEY"] = "your key here"


class HumanInputAgent:

    def run(self, state):
        return state

    def input_genre(self, state):
        print("sure, can you please choose movie genre: drama, thriller, documentary, comedy, crime, reality-tv, horror, sport, animation")
        return {"input_genre_message": "sure, can you please enter movie genre"}


class StartAgent:
    name = 'start'

    def run(self, dummy):
        print("Hi! I can help with movie recommendations")
        return {"entry_message": "Hi! I can help with movie recommendations"}


class OutputAgent:
    def run(self, state: dict):
        state['quit'] = True
        return state


class MovieRecommendationsAgent:

    def run(self, state):
        from langchain_openai import ChatOpenAI
        import pandas as pd
        train_data = pd.read_csv("train_data.txt", sep=':::', names=['Title', 'Genre', 'Description'], engine='python')
        filtered_data = train_data[train_data['Genre'].str.strip() == state["input_genre_message_input"]]
        print(filtered_data.head(10))
        llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=2,
            api_key="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",  # if you prefer to pass api key in directly instaed of using env vars
        )
        messages = [
            (
                "system",
                "You are a helpful assistant that helps recommending movies based on genre",
            ),
            (
                "system",
                f"answer based on only this context: {filtered_data}"
            ),
            ("human", f"{state["input_genre_message_input"]}"),
        ]
        ai_msg = llm.invoke(messages)
        state['message'] = ai_msg
        print(ai_msg.content)
        return state


class StateMachine:
    def __init__(self, api_key=None):
        import os
        from langgraph.checkpoint.sqlite import SqliteSaver
        import sqlite3

        def from_conn_stringx(cls, conn_string: str, ) -> "SqliteSaver":
            return SqliteSaver(conn=sqlite3.connect(conn_string, check_same_thread=False))

        SqliteSaver.from_conn_stringx = classmethod(from_conn_stringx)

        self.memory = SqliteSaver.from_conn_stringx(":memory:")

        start_agent = StartAgent()
        human_input_agent = HumanInputAgent()
        output_agent = OutputAgent()
        movie_agent = MovieRecommendationsAgent()

        workflow = Graph()

        workflow.add_node(start_agent.name, start_agent.run)
        workflow.add_node("human_input_agent", human_input_agent.run)
        workflow.add_node("input_genre", human_input_agent.input_genre)
        workflow.add_node("MovieRecommendationsAgent", movie_agent.run)
        workflow.add_node("output_agent", output_agent.run)

        workflow.add_edge(start_agent.name, "human_input_agent")
        workflow.add_edge("human_input_agent", "input_genre")
        workflow.add_edge("input_genre", "MovieRecommendationsAgent")
        workflow.add_edge("MovieRecommendationsAgent", "output_agent")

        # set up start and end nodes
        workflow.set_entry_point(start_agent.name)
        workflow.set_finish_point("output_agent")

        self.thread = {"configurable": {"thread_id": "2"}}
        self.chain = workflow.compile(checkpointer=self.memory, interrupt_after=[start_agent.name, "input_genre"])
        # self.chain.get_graph().draw_png("mm_agent.png")

    def start(self):
        result = self.chain.invoke("", self.thread)
        # print("*",self.chain.get_state(self.thread),"*")
        # print("r",result)
        if result is None:
            values = self.chain.get_state(self.thread).values
            last_state = next(iter(values))
            return values[last_state]
        return result

    def resume(self, new_values: dict):
        values = self.chain.get_state(self.thread).values
        # last_state=self.chain.get_state(self.thread).next[0].split(':')[0]
        last_state = next(iter(values))
        # print(self.chain.get_state(self.thread))
        values[last_state].update(new_values)
        self.chain.update_state(self.thread, values[last_state])
        result = self.chain.invoke(None, self.thread, output_keys=last_state)
        # print("r",result)
        if result is None:
            values = self.chain.get_state(self.thread).values
            last_state = next(iter(values))
            return self.chain.get_state(self.thread).values[last_state]
        return result


if __name__ == '__main__':  # test code

    sm = StateMachine()
    result = sm.start()
    while "quit" not in result:
        last_key = next(reversed(result))
        user_input = input(f"Enter your input {last_key}: ")
        result = sm.resume({f"{last_key}_input": user_input})
