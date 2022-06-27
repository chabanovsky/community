import re

import pandas as pd
import numpy as np
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta

from bokeh.io import show
from bokeh.models import ColumnDataSource, FactorRange
from bokeh.plotting import figure
from bokeh.palettes import Spectral5


import bokeh.io
bokeh.io.output_notebook()

from google.colab import drive
from google.colab import auth
import gspread
from google.auth import default

import report 

class AnnouncementChecklist:
    def __init__(self):
        self._story = False
        self._only_one_theme = False
        self._shorter_than_one_and_half_pages = False
        self._positively_present = False
        self._from_user_perspective = False
        self._clear_cta_or_question = False
        self._easy_to_read = False

    def _fields_to_array(self):
        return [
            self._story,
            self._only_one_theme,
            self._shorter_than_one_and_half_pages,
            self._positively_present,
            self._from_user_perspective,
            self._clear_cta_or_question,
            self._easy_to_read
        ]
    
    def get_score(self):
        return np.sum([int(field) for field in self._fields_to_array()])

    def get_max_score(self):
            return np.sum([1 for _ in self._fields_to_array()])        

class SpreadsheetData:
    def __init__(self, spreadsheet_id):
        self.creds, _ = default()
        self.gc = gspread.authorize(self.creds)
        self.speadsheet = self.gc.open_by_key(spreadsheet_id)

    def feedback(self, question_id):
        for sheet in self.speadsheet.worksheets():
            title = sheet.title

            pattern = 'meta.stack(overflow|exchange).com/(q|questions)/\d+'
            if len(re.findall(pattern, title)) == 0:
                continue

            numbers = re.findall('\d+', title)
            if len(numbers) == 0:
                continue

            sheet_id = int(numbers[0])
            if sheet_id != question_id:
                continue

            values = sheet.get_all_values()
            df = pd.DataFrame(data=values)
            df.columns = df.iloc[0]
            df = df.drop(df.index[0])

            df["AnswerId"] = df["Link"].apply(lambda x: int(re.findall('\d+', x)[0]))
            df["QuestionId"] = question_id
            df["Theme"] = df["Theme"].fillna("n/a")
            df["Theme"] = df["Theme"].replace("", "n/a")
            return df

        return None            


############################################

class MainSiteData:
    def __init__(self, db_name, project_path_prefix):
        self.project_folder = "%s/%s" % (project_path_prefix, db_name)
        self._upload_data()
        self._correct_types()
        self._new_fields()

    def _upload_data(self):
        self.actions = pd.read_csv("%s/monthly_actions.csv" % (self.project_folder))         

    def _correct_types(self):
        self.actions["OnDate"] = pd.to_datetime(
            self.actions["OnDate"]
        )
        self.actions["UserId"] = self.actions["UserId"].fillna(-1).astype(int)
        self.actions["AccountId"] = self.actions["AccountId"].fillna(-1).astype(int)
        self.actions.drop_duplicates(subset=['OnDate', "UserId"], inplace=True)

    def _new_fields(self):
        # Categorization:
        # 1 engagment point = question or answer or 1/5 * comment or 1/5 edits or 1/10 votes / flags / reviews
        # Active: any type of actions
        # Engaged: 1 engagment point
        # Very engaged: 10 * Engaged
        # Core: 10 * Very engaged
        self.actions["EngagementPoints"] = self.actions["Questions"] + self.actions["Answers"] + 1/5. * self.actions["Comments"] + 1/5. * self.actions["Edits"] + 1/10. * (
            self.actions["AcceptVotes"] + 
            self.actions["UpVotes"] + 
            self.actions["DownVotes"] + 
            self.actions["CommentVotes"] + 
            self.actions["CloseVotes"] + 
            self.actions["ReopenVotes"] + 
            self.actions["OtherFlags"]+ 
            self.actions["Reviews"]
        )        

class MetaData:
    def __init__(self, spreadsheet_id, db_name, questions_in_the_series, project_path_prefix):
        self.spreadsheet_id = spreadsheet_id
        self.questions_in_the_series = questions_in_the_series
        self.project_folder = "%s/%s" % (project_path_prefix, db_name)
        self._upload_data()
        self._correct_types()
        self._new_fields()

    def _upload_data(self):
        self.users = pd.read_csv("%s/users.csv" % (self.project_folder)) 
        self.posts = pd.read_csv("%s/posts.csv" % (self.project_folder)) 
        self.post_votes = pd.read_csv("%s/post_votes.csv" % (self.project_folder)) 
        self.comments = pd.read_csv("%s/comments.csv" % (self.project_folder)) 
        self.comment_votes = pd.read_csv("%s/comment_votes.csv" % (self.project_folder)) 
        self.moderators = pd.read_csv("%s/moderators.csv" % (self.project_folder)) 
        self.employees = pd.read_csv("%s/employee_accounts.csv" % (self.project_folder)) 

        self.feedback_source = SpreadsheetData(self.spreadsheet_id)


    def _correct_types(self):
        self.comment_votes["CreationDate"] = pd.to_datetime(
            self.comment_votes["CreationDate"]
        )
        self.comment_votes["DeletionDate"] = pd.to_datetime(
            self.comment_votes["DeletionDate"]
        )        
        self.users["CreationDate"] = pd.to_datetime(
            self.users["CreationDate"]
        )
        self.posts["CreationDate"] = pd.to_datetime(
            self.posts["CreationDate"]
        )
        self.posts["DeletionDate"] = pd.to_datetime(
            self.posts["DeletionDate"]
        )
        self.post_votes["CreationDate"] = pd.to_datetime(
            self.post_votes["CreationDate"]
        )
        self.post_votes["DeletionDate"] = pd.to_datetime(
            self.post_votes["DeletionDate"]
        )
        self.comments["CreationDate"] = pd.to_datetime(
            self.comments["CreationDate"]
        )
        self.comments["DeletionDate"] = pd.to_datetime(
            self.comments["DeletionDate"]
        )
        self.comments["Score"] = self.comments["Score"].fillna(0).astype(int)
        self.comments["UserId"] = self.comments["UserId"].fillna(-1).astype(int)
        self.post_votes["TargetUserId"] = self.post_votes["TargetUserId"].fillna(-1).astype(int)

        # self.users.loc[self.users["Id"].isin(employees), "UserTypeId"] = 5
        self.users.loc[self.users["AccountId"].isin(self.employees["AccountId"]), "UserTypeId"] = 5
        self.users["IsModerator"] = False
        self.users.loc[self.users["AccountId"].isin(self.moderators["AccountId"].unique()), "IsModerator"] = True

    def _new_fields(self):
        self.posts["Empty"] = ""
        '''
        Let us calculate action counts
        '''      
        tmp = pd.merge(
            self.comments, 
            self.comment_votes.groupby(by=["PostCommentId"])["Id"].nunique().rename("CommentVoteCount").to_frame(),
            left_on="Id", right_on="PostCommentId", how="left")
        tmp['CommentVoteCount'] = tmp['CommentVoteCount'].fillna(0).astype(int)
        self.comments = tmp

        tmp = pd.merge(
            self.posts, 
            self.post_votes.groupby(by=["PostId"])["Id"].nunique().rename("PostVoteCount").to_frame(),
            left_on="Id", right_on="PostId", how="left")
        tmp['PostVoteCount'] = tmp['PostVoteCount'].fillna(0).astype(int)
        self.posts = tmp

        tmp = pd.merge(
            self.posts, 
            self.comments.groupby(by=["PostId"])["Id"].nunique().rename("PostCommentCount").to_frame(),
            left_on="Id", right_on="PostId", how="left")
        tmp['PostCommentCount'] = tmp['PostCommentCount'].fillna(0).astype(int)
        self.posts = tmp  

        tmp = pd.merge(
            self.posts, 
            self.comments.groupby(by=["PostId"])["CommentVoteCount"].sum().rename("PostCommentVoteCount").to_frame(),
            left_on="Id", right_on="PostId", how="left")
        tmp['PostCommentVoteCount'] = tmp['PostCommentVoteCount'].fillna(0).astype(int)             
        self.posts = tmp

        answers = self.posts[self.posts["PostTypeId"] == 2]
        tmp = pd.merge(
            self.posts, 
            answers.groupby(by=["ParentId"])["Id"].nunique().rename("AnswerCount").to_frame(),
            left_on="Id", right_on="ParentId", how="left")
        tmp['AnswerCount'] = tmp['AnswerCount'].fillna(0).astype(int)
        self.posts = tmp

        self.posts["PostActionCount"] = self.posts["PostVoteCount"] + self.posts["PostCommentCount"] + self.posts["PostCommentVoteCount"]

        answers = self.posts[self.posts["PostTypeId"] == 2]
        tmp = pd.merge(
            self.posts, 
            answers.groupby(by=["ParentId"])["PostActionCount"].sum().rename("AllAnswersActionCount").to_frame(),
            left_on="Id", right_on="ParentId", how="left")
        tmp['AllAnswersActionCount'] = tmp['AllAnswersActionCount'].fillna(0).astype(int)
        self.posts = tmp

        self.posts["TotalQuestionActionCount"] = self.posts["PostActionCount"] + self.posts["AllAnswersActionCount"] 
        self.posts.loc[self.posts["PostTypeId"] == 2, "TotalQuestionActionCount"] = 0

        self.posts = pd.merge(
            self.posts,
            self.users[['Id', 'UserTypeId', "Reputation", "IsModerator"]].rename(columns={"Id":"OwnerUserId"}),
            left_on="OwnerUserId", right_on="OwnerUserId", how="left")

        feedback_list = list()
        for id in self.questions_in_the_series:
            f = self.feedback_source.feedback(id)
            if f is None:
                continue
            feedback_list.append(f)

        self.all_feedback = pd.merge(
            self.posts, pd.concat(feedback_list, axis=0), 
            left_on="Id", right_on="AnswerId", how="inner"
        )
        self.all_feedback["Theme"] = self.all_feedback["Theme"].astype(str)


        ###############################################################################

class Grader:
    def __init__(self, question_id, main_site, meta_site):
        self.question_id = question_id
        self.main_site = main_site
        self.meta_site = meta_site

        self._checklist_grade = 'red'
        self._reach_grade = 'red'  
        self._feedback_grade = 'red'      

        self._view_count = 0
        self._interest = 0
        self._feedback_result = None

    def set_checklist(self, checklist):
        self.checklist = checklist

    def checlist_grade(self):
        # Categorization:
        #   6-7: green
        #   4-5: yellow
        #   3 and less: red

        value = self.checklist.get_score()
        max_value = self.checklist.get_max_score()
        grade = "yellow"
        if value >= 6: 
            grade = "green"
        elif value <= 3: 
            grade = "red"
        self._checklist_grade = grade
        return grade, value, max_value
      
    def reach_grade(self):
        def _get_score(df, question_id, field):
            value = df[df["Id"] == question_id][field].values[0]
            return np.mean(df[field] < value)

        employee_ids = self.meta_site.users[self.meta_site.users["UserTypeId"] == 5]["AccountId"].unique()
        employee_posts = self.meta_site.posts[(self.meta_site.posts["AccountId"].isin(employee_ids)) & (self.meta_site.posts["PostTypeId"] == 1)]

        # Categorization:
        #   If both better, go grean
        #   If any worse, go red
        #   Everything else is yellow

        view_count = 100 * _get_score(employee_posts, self.question_id, "ViewCount")
        interest = 100 * _get_score(employee_posts, self.question_id, "TotalQuestionActionCount")

        grade = "yellow"
        if (view_count >= 80 and interest > 50) or (view_count > 50 and interest >= 80): grade = "green"
        elif view_count < 50 or interest < 50: grade = "red"

        self._reach_grade = grade
        self._view_count = view_count
        self._interest = interest

        return grade, view_count, interest

    def feedback_grade(self):
        feedback = self.meta_site.all_feedback[self.meta_site.all_feedback["QuestionId"] == self.question_id]

        total = feedback["Score"].sum()
        pos = feedback[feedback["Mood"] == "positive"]["Score"].sum()
        neg = feedback[feedback["Mood"] == "negative"]["Score"].sum()
        neu = feedback[feedback["Mood"] == "neutral"]["Score"].sum()

        results = [
            pos / float(total) * 100,
            neu / float(total) * 100,
            neg / float(total) * 100
        ]

        grade = "yellow"
        if results[0] >= 50: grade = "green"
        elif results[2] >= 50: grade = "red"

        self._feedback_grade = grade
        self._feedback_result = results

        return grade, results

###############################################################################

class QuestionFeedback:
    def __init__(self, main_site, meta_site, question_id):
        self.question_id = question_id
        self.meta_site = meta_site
        self.main_site = main_site
        self.q_data = meta_site.all_feedback[meta_site.all_feedback["ParentId"] == question_id]

    def themes(self, n_top=3):
        def _get_themes(df, question_id, mood):
            feedback = df[(df["QuestionId"] == question_id) & (df["Mood"] == mood)]
            tmp = feedback.groupby(by=["Theme"])["AnswerId"].count().rename("ThemeCount").to_frame().reset_index()
            tmp = tmp.sort_values(by=["ThemeCount"], ascending=False)
            result = list()
            for _, row in tmp.iterrows():
                result.append((row["Theme"], row["ThemeCount"]))
            return result

        def _get_top_themes(df, question_id, n):
            feedback = df[df["QuestionId"] == question_id]
            tmp = feedback.groupby(by=["Theme"])["AnswerId"].count().rename("ThemeCount").to_frame().reset_index()
            return tmp.sort_values(by=["ThemeCount"], ascending=False).head(n)["Theme"].unique().tolist()

        top = _get_top_themes(self.meta_site.all_feedback, self.question_id, n_top)
        positive = _get_themes(self.meta_site.all_feedback, self.question_id, "positive")
        neutral = _get_themes(self.meta_site.all_feedback, self.question_id, "neutral")
        negative = _get_themes(self.meta_site.all_feedback, self.question_id, "negative")

        return top, positive, neutral, negative

    def print_theme_stats(self, n_top=3):
        top, positive, neutral, negative = self.themes(n_top)
        top_str = ""
        for theme in top:
            if len(top_str) > 0:
                top_str += ","
            top_str += " %s" % theme

        print("Top themes: %s" % (top_str))

        print("Positive")
        for (theme, cnt) in positive:
            print("- %s: %d" % (theme, cnt))

        print("Negative")
        for (theme, cnt) in negative:
            print("- %s: %d" % (theme, cnt))

        print("Neutural")
        for (theme, cnt) in neutral:
            print("- %s: %d" % (theme, cnt))


    def domain_experts(self, domain_actions_threshold):

        the_date = self.meta_site.posts[self.meta_site.posts["Id"] == self.question_id]["CreationDate"].values[0]

        ts = pd.to_datetime(str(the_date)) 
        threshold = ts - relativedelta(months=1)

        tmp = self.main_site.actions[(self.main_site.actions["OnDate"] > threshold) & (self.main_site.actions["OnDate"] < ts)]
        # Lest us check that we are looking at only one month of data.
        # If we want to do it for a longer period
        # we will need to redo the logic with EngagementPoints

        assert(tmp["OnDate"].nunique() == 1)

        active_users = tmp
        engaged_users = tmp[tmp["EngagementPoints"] >= 1]
        very_engaged_users = tmp[tmp["EngagementPoints"] >= 10]
        core_users = tmp[tmp["EngagementPoints"] >= 100]

        print("Engaged users on the main site on the month prior posting the announcement:")
        print("- Active: %d" % (len(active_users.index)))
        print("- Engaged: %d (%0.2f%%)" % (len(engaged_users.index), float(len(engaged_users.index))/len(active_users.index) * 100))
        print("- Very engaged: %d (%0.2f%%)" % (len(very_engaged_users.index), float(len(very_engaged_users.index))/len(active_users.index) * 100))
        print("- Core: %d (%0.2f%%)" % (len(core_users.index), float(len(core_users.index))/len(active_users.index) * 100))

        # Collecting all actions on the target question
        answers_df = self.meta_site.posts[self.meta_site.posts["ParentId"] == self.question_id]
        posts_ids = answers_df["Id"].unique().tolist() + [self.question_id]
        post_votes_df = self.meta_site.post_votes[self.meta_site.post_votes["PostId"].isin(posts_ids)]
        comments_df = self.meta_site.comments[self.meta_site.comments["PostId"].isin(posts_ids)]
        commnet_votes_df = self.meta_site.comment_votes[self.meta_site.comment_votes["PostCommentId"].isin(comments_df["Id"])]

        # TBD: Remove employees!
        participants_ids = list(set(answers_df["OwnerUserId"].values.tolist() + post_votes_df["UserId"].values.tolist() + comments_df["UserId"].values.tolist() + commnet_votes_df["UserId"].values.tolist()))

        active_meta = active_users[active_users["UserId"].isin(participants_ids)]
        engaged_meta = engaged_users[engaged_users["UserId"].isin(participants_ids)]
        very_engaged_meta = very_engaged_users[very_engaged_users["UserId"].isin(participants_ids)]
        core_meta = core_users[core_users["UserId"].isin(participants_ids)]

        print("Users that somehow acted on the meta post (%d total):" % (len(participants_ids)))
        print(" - Active: %d" % (len(active_meta.index)))
        print(" - Engaged: %d" % (len(engaged_meta.index)))
        print(" - Very engaged: %d" % (len(very_engaged_meta.index)))
        print(" - Core: %d" % (len(core_meta.index)))

        positive_answer_users = self.meta_site.all_feedback[self.meta_site.all_feedback["Mood"] == "positive"]["OwnerUserId"].values.tolist()
        negative_answer_users = self.meta_site.all_feedback[self.meta_site.all_feedback["Mood"] == "negative"]["OwnerUserId"].values.tolist()
        neutral_answer_users = self.meta_site.all_feedback[self.meta_site.all_feedback["Mood"] == "neutral"]["OwnerUserId"].values.tolist()

        positive_ids = list(set(positive_answer_users))
        negative_ids = list(set(negative_answer_users))
        neutral_ids = list(set(neutral_answer_users))

        def print_domain_experts_reach(df, active_users, domain_actions_threshold, field, title, positive_ids, negative_ids, neutral_ids):
            tmp = active_users[active_users[field] >= domain_actions_threshold]
            print("%d active %s have participated (all actions) in the post (%0.2f%% of all active %s on the main site)." % (
                df[df[field] >= domain_actions_threshold]["UserId"].nunique(),
                title.lower(), 
                100 * (df[df[field] >= domain_actions_threshold]["UserId"].nunique() / float(tmp["UserId"].nunique())),
                title.lower()
            ))

            tmp = df[df[field] >= domain_actions_threshold]
            all = tmp[tmp["UserId"].isin(set(positive_ids + negative_ids + neutral_ids))]["UserId"].unique()
            print("%s' answers (total users %d):" % (title, len(all)))
            
            pos = tmp[tmp["UserId"].isin(positive_ids)]["UserId"].unique()
            print("- Positive: %d " % (len(pos)))
            neg = tmp[tmp["UserId"].isin(negative_ids)]["UserId"].unique()
            print("- Negative: %d " % (len(neg)))
            neu = tmp[tmp["UserId"].isin(neutral_ids)]["UserId"].unique()
            print("- Neutral: %d " % (len(neu)))    


        # TBD:  Currently we are looking at the last month experts
        #       It seems we should include a bigger period

        print("\r\n\r\nDomain experts that have been active on the main site one month prior the announcement\r\n")
        print_domain_experts_reach(
            active_meta, 
            active_users, 
            domain_actions_threshold, 
            "Reviews", "Reviewers", 
            positive_ids, negative_ids, 
            neutral_ids
        )
        print("\r\n")
        print_domain_experts_reach(
            active_meta, 
            active_users, 
            domain_actions_threshold, 
            "Answers", "Answer givers", 
            positive_ids, negative_ids, 
            neutral_ids
        )
        print("\r\n")
        print_domain_experts_reach(
            active_meta, 
            active_users, 
            domain_actions_threshold, 
            "Edits", "Editors", 
            positive_ids, negative_ids, 
            neutral_ids
        )            

    def responses_on_scatter_plot(self, df=None, coef=70):
        def _dfs(data, coef=70):
            df = data[data["PostTypeId"] == 2].copy()

            df["Size"] = df["Score"].abs()/np.linalg.norm(df["Score"].abs()) * coef

            pos_mod   = df[(df["Mood"] != "negative") & (df["IsModerator"])]
            neg_mod   = df[(df["Mood"] == "negative") & (df["IsModerator"])]
            pos_users = df[(df["Mood"] != "negative") & (~df["IsModerator"])]
            neg_users = df[(df["Mood"] == "negative") & (~df["IsModerator"])]

            return [
              (pos_mod, "diamond", "green"),
              (neg_mod, "diamond", "#ee6666"),
              (pos_users, "circle", "green"),
              (neg_users, "circle", "#ee6666")
            ]

        def _xaxis():
            return "Reputation"

        def _yaxis():
            return "PostActionCount"

        def _tooltips():
            return [
              ('PostId', '@Id'),
              ('Score', '@Score'),
              ('Username', '@DisplayName'),
              ('Theme', '@Theme')
            ] 

        report.scatter_plot(
            _dfs(self.q_data), 
            "Users' feedback", 
            "Authority (Reputation)",
            "Interest (Number Of Comments, Votes, And Comment Votes)",
            _tooltips(),
            _xaxis(),
            _yaxis(),
            "DisplayName")  
        
###############################################################################

class SeriesFeedback:
    def __init__(self, data):
        self.data = data
        self.posts = data.posts[(data.posts["Id"].isin(data.questions_in_the_series)) | (data.posts["ParentId"].isin(data.questions_in_the_series))]
        self.post_votes = data.post_votes[data.post_votes["PostId"].isin(self.posts["Id"].unique())]
        self.comments = data.comments[data.comments["PostId"].isin(self.posts["Id"].unique())]
        self.comment_votes = data.comment_votes[data.comment_votes["PostCommentId"].isin(self.comments["Id"].unique())]
        self.users = data.users[
            (data.users["Id"].isin(self.posts["OwnerUserId"].unique())) |
            (data.users["Id"].isin(self.comments["UserId"].unique())) |
            (data.users["Id"].isin(self.comment_votes["UserId"].unique()))|
            (data.users["Id"].isin(self.post_votes["UserId"].unique()))
        ]

    def basic_stats(self):
        print("Unique users participated in the series")
        print("- Total: %d" % (self.users["Id"].nunique()))
        print("- Askers: %d" % (self.posts[self.posts["PostTypeId"] == 1]["OwnerUserId"].nunique()))
        print("- Answer Givers: %d" % (self.posts[self.posts["PostTypeId"] == 2]["OwnerUserId"].nunique()))
        # 2 Up, 3 Down, 5 Bookmark, 21 follow
        print("- Post Voters: %d" % (self.post_votes[self.post_votes["VoteTypeId"].isin([2, 3])]["UserId"].nunique()))
        print("- Post Bookmark / Follow: %d" % (self.post_votes[self.post_votes["VoteTypeId"].isin([5, 21])]["UserId"].nunique()))
        print("- Commentators: %d" % (self.comments["UserId"].nunique()))
        print("- Comment Voters: %d" % (self.comment_votes["UserId"].nunique()))

        print("\r\n")
        print("Actions:")
        print("- Questions: %d" % (self.posts[self.posts["PostTypeId"] == 1]["Id"].nunique()))
        print("- Answers: %d" % (self.posts[self.posts["PostTypeId"] == 2]["Id"].nunique()))
        print("- Post Votes: %d" % (self.post_votes[self.post_votes["VoteTypeId"].isin([2, 3])]["Id"].nunique()))
        print("- Post Bookmark / Follow: %d" % (self.post_votes[self.post_votes["VoteTypeId"].isin([5, 21])]["Id"].nunique()))
        print("- Comments: %d" % (self.comments["Id"].nunique()))
        print("- Comment Votes: %d" % (self.comment_votes["Id"].nunique()))


    def feedback_plot(self):
        def _dfs(data, coef=70):
            df = data.posts[data.posts["PostTypeId"] == 1].copy()
            df = df.sort_values(by=["Id"], ascending=True)
            df["Empty"] = ["Q #" + str(serial_num) for serial_num in range(1, len(df.index)+1)]
            df["Size"] = df["Score"].abs()/np.linalg.norm(df["Score"].abs()) * coef

            pos_employees = df[(df["Score"] >= 0) & (df["UserTypeId"] == 5)]
            neg_employees = df[(df["Score"] < 0) & (df["UserTypeId"] == 5)]
            pos_users =     df[(df["Score"] >= 0) & (df["UserTypeId"] < 5)]
            neg_users =     df[(df["Score"] < 0) & (df["UserTypeId"] < 5)]

            return [
              (pos_employees, "diamond", "green"),
              (neg_employees, "diamond", "#ee6666"),
              (pos_users, "circle", "green"),
              (neg_users, "circle", "#ee6666")
            ]

        def _xaxis():
            return "ViewCount"

        def _yaxis():
            return "TotalQuestionActionCount"

        def _tooltips():
            return [
                #('Creation Date', '@CreationDate'),
                ('Score', '@Score'),
                ("Author", "@DisplayName"),
                ("Interest", "@TotalQuestionActionCount"),
                ("Pageviews", "@ViewCount"),
                ("Title", "@Title")
            ] 

        report.scatter_plot(
            _dfs(self), 
            "Reach, Egagement, And Perception Of Questions", 
            "Page views",
            "Interest (Number Of Answers, Comments, Votes)",
            _tooltips(),
            _xaxis(),
            _yaxis(),
            "Empty")    
        
    # https://docs.bokeh.org/en/latest/docs/user_guide/categorical.html#nested-categories
    def question_info(self):
        questions = self.posts[(self.posts["PostTypeId"] == 1) & (self.posts["UserTypeId"] == 5)].sort_values(by=["CreationDate"])
        serial_numbers = ["Q #%d" % index for index in range(1, len(questions.index) + 1)]
        metrics = ['Score', 'Interest']

        col_data = {
            'SerialNumbers': serial_numbers,
            'Score': questions["Score"].values,
            'Interest': questions["TotalQuestionActionCount"].values
        }

        # this creates [ ("Apples", "2015"), ("Apples", "2016"), ("Apples", "2017"), ("Pears", "2015), ... ]
        x = [ (number, metric) for number in serial_numbers for metric in metrics]
        counts = sum(zip(col_data['Score'], col_data['Interest']), ()) # like an hstack

        source = ColumnDataSource(data=dict(x=x, counts=counts))
        p = figure(x_range=FactorRange(*x), height=report.PLOT_HEIGHT, width=report.PLOT_WIDTH, title="Score & Interest Of Announcements")

        p.vbar(x='x', top='counts', width=0.9, source=source)

        p.x_range.range_padding = 0.1
        p.xaxis.major_label_orientation = 1
        p.xgrid.grid_line_color = None
        show(p)
        for index, (_, row) in enumerate(questions.iterrows()):
            print("Q #%d https://meta.stackoverflow.com/q/%d | %s " % (index + 1, row['Id'], row["Title"]))


    def question_info_sep(self):
        def _plot_metric(data, column_name, title):
            questions = data.posts[(data.posts["PostTypeId"] == 1) & (data.posts["UserTypeId"] == 5)].sort_values(by=["CreationDate"])

            serial_numbers = ["Q #%d" % index for index in range(1, len(questions.index) + 1)]
            p = figure(x_range=serial_numbers, 
                      height=report.PLOT_HEIGHT, 
                      width=report.PLOT_WIDTH, 
                      title=title)
            p.vbar(x=serial_numbers, top=questions[column_name].values, width=0.9)
            p.xgrid.grid_line_color = None
            show(p)

        _plot_metric(self, "Score", "Score Of The Questions")
        _plot_metric(self, "TotalQuestionActionCount", "Interest (Answers, Comments, Votes)")


    # https://docs.bokeh.org/en/latest/docs/user_guide/categorical.html#nested-categories
    def question_user_info(self):
        questions = self.posts[(self.posts["PostTypeId"] == 1) & (self.posts["UserTypeId"] == 5)].sort_values(by=["CreationDate"])
        question_ids = questions["Id"].values.tolist()
        serial_numbers = ["Q #%d" % index for index in range(1, len(questions.index) + 1)]

        metrics = ['Content', 'Votes']
        alls = list()
        contents = list()
        voters = list()
        for question_id in question_ids:
            all, content, votes = self._question_users(question_id)                       
            alls.append(len(set(all)))
            contents.append(len(set(content))) 
            voters.append(len(set(votes))) 

        col_data = {
            'SerialNumbers': serial_numbers,
            'Content': contents,
            'Votes': voters
        }

        x = [ (number, metric) for number in serial_numbers for metric in metrics]
        counts = sum(zip(col_data['Content'], col_data['Votes']), ()) 

        source = ColumnDataSource(data=dict(x=x, counts=counts))
        p = figure(x_range=FactorRange(*x), height=report.PLOT_HEIGHT, width=report.PLOT_WIDTH, title="Unique Users For Content (Answers & Comments) And Votes")

        p.vbar(x='x', top='counts', width=0.9, source=source)

        p.x_range.range_padding = 0.1
        p.xaxis.major_label_orientation = 1
        p.xgrid.grid_line_color = None
        show(p)

    # https://docs.bokeh.org/en/latest/docs/user_guide/categorical.html#nested-categories
    def question_percent_of_content_per_downvote(self):
        questions = self.posts[(self.posts["PostTypeId"] == 1) & (self.posts["UserTypeId"] == 5)].sort_values(by=["CreationDate"])
        question_ids = questions["Id"].values.tolist()
        serial_numbers = ["Q #%d" % index for index in range(1, len(questions.index) + 1)]

        percents = list()
        downvoter_num = list()

        for question_id in question_ids:
            _, content, _ = self._question_users(question_id)                       
            content_user_ids = set(content)
            downvoters = self.post_votes[(self.post_votes['PostId'] == question_id) & (self.post_votes['VoteTypeId'] == 3)]["UserId"].unique()
            downvoter_num.append(len(downvoters))
            down_and_content = list(set(downvoters).intersection(content_user_ids))
            percents.append( len(down_and_content) / float(len(downvoters)) * 100)

        p = figure(x_range=serial_numbers, 
                  height=report.PLOT_HEIGHT, 
                  width=report.PLOT_WIDTH, 
                  title="Percentage Of Downvoters Who Posted A Comment Or An Answer")
        
        p.vbar(x=serial_numbers, top=percents, width=0.9)
        p.xgrid.grid_line_color = None
        show(p)
        for index, value in enumerate(downvoter_num):
            print("Q #%d, %d downvotes" % (index + 1, value))

    # https://docs.bokeh.org/en/latest/docs/user_guide/categorical.html#nested-categories
    def question_downvoters_rep(self):
        questions = self.posts[(self.posts["PostTypeId"] == 1) & (self.posts["UserTypeId"] == 5)].sort_values(by=["CreationDate"])
        question_ids = questions["Id"].values.tolist()
        serial_numbers = ["Q #%d" % index for index in range(1, len(questions.index) + 1)]

        metrics = ['Mean', 'Median']
        medians = list()
        means = list()
        for question_id in question_ids:
            downvoters = self.post_votes[(self.post_votes['PostId'] == question_id) & (self.post_votes['VoteTypeId'] == 3)]["UserId"].unique()
            downvoter_users = self.users[self.users["Id"].isin(downvoters)]
            downvoter_users = downvoter_users[downvoter_users["Reputation"] < downvoter_users["Reputation"].quantile(0.95)]
            rep = downvoter_users["Reputation"]
            medians.append(rep.median())
            means.append(rep.mean())

        col_data = {
            'SerialNumbers': serial_numbers,
            'Means': means,
            'Medians': medians
        }

        x = [ (number, metric) for number in serial_numbers for metric in metrics]
        counts = sum(zip(col_data['Means'], col_data['Medians']), ()) 

        source = ColumnDataSource(data=dict(x=x, counts=counts))
        p = figure(x_range=FactorRange(*x), height=report.PLOT_HEIGHT, width=report.PLOT_WIDTH, title="Downvoters' Average Reputation")

        p.vbar(x='x', top='counts', width=0.9, source=source)

        p.x_range.range_padding = 0.1
        p.xaxis.major_label_orientation = 1
        p.xgrid.grid_line_color = None
        show(p)

    def new_users(self):
        question_users = list()
        for question_id in sorted(self.data.questions_in_the_series, reverse=False):
            post_ids = self.data.posts[self.data.posts["ParentId"] == question_id]["Id"].values.tolist()
            answer_givers = self.data.posts[self.data.posts["Id"].isin(post_ids)]["OwnerUserId"].values.tolist()
            post_voters = self.data.post_votes[self.data.post_votes["PostId"].isin(post_ids + [question_id])]["UserId"].values.tolist()
            comments = self.data.comments[self.data.comments["PostId"].isin(post_ids + [question_id])]
            commenters = comments["UserId"].values.tolist()
            comment_voters = self.data.comment_votes[self.data.comment_votes["PostCommentId"].isin(comments["Id"])]["UserId"].values.tolist()
            all_users = answer_givers + commenters + post_voters + comment_voters
            question_users.append((question_id, all_users))

        questions = list()
        new_values = list()
        total_values = list()
        all_past_users = set()
        for (question, users) in question_users:
            current_users = list(set(users) - all_past_users)
            all_past_users = set(list(all_past_users) + current_users)

            questions.append(question)
            new_values.append(len(current_users))
            total_values.append(len(set(users)))

        serial_numbers = ["Q #%d" % index for index in range(1, len(questions) + 1)]
        metrics = ['Total', 'New']

        col_data = {
            'SerialNumbers': serial_numbers,
            'Total': total_values,
            'New': new_values
        }

        # this creates [ ("Apples", "2015"), ("Apples", "2016"), ("Apples", "2017"), ("Pears", "2015), ... ]
        x = [ (number, metric) for number in serial_numbers for metric in metrics]
        counts = sum(zip(col_data['Total'], col_data['New']), ()) # like an hstack
        source = ColumnDataSource(data=dict(x=x, counts=counts))
        p = figure(
            x_range=FactorRange(*x), 
            height=report.PLOT_HEIGHT, 
            width=report.PLOT_WIDTH, 
            title="Number of new users participated in a question"
        )
        p.vbar(x='x', top='counts', width=0.9, source=source)

        p.x_range.range_padding = 0.1
        p.xaxis.major_label_orientation = 1
        p.xgrid.grid_line_color = None
        show(p)

    def _comment_voters(self, comment_id):
        return self.comment_votes[self.comment_votes["PostCommentId"] == comment_id]["UserId"].values.tolist()
    
    def _post_voters(self, post_id):
        return self.post_votes[self.post_votes['PostId'] == post_id]["UserId"].values.tolist()

    def _commentators(self, post_id):
        return self.comments[self.comments["PostId"] == post_id]["UserId"].values.tolist()

    def _answer_givers(self, question_id):
        return self.posts[self.posts["ParentId"] == question_id]["OwnerUserId"].values.tolist()

    # return: all, content, voters
    def _question_users(self, question_id):
        answer_givers = self._answer_givers(question_id)
        question_commentators = self._commentators(question_id)
        question_voters = self._post_voters(question_id)
        # TBD: question comment voters
        question_comment_voters = list()
        comment_ids = self.comments[self.comments["PostId"] == question_id]["Id"].unique()
        for comment_id in comment_ids:
            question_comment_voters.extend(self._comment_voters(comment_id))

        answer_ids = self.posts[self.posts["ParentId"] == question_id]["Id"].unique()
        answer_comentators = list()
        answer_voters = list()
        answer_comment_voters = list()

        for answer_id in answer_ids:
            answer_comentators.extend(self._commentators(answer_id))
            answer_voters.extend(self._post_voters(answer_id))
            comment_ids = self.comments[self.comments["PostId"] == answer_id]["Id"].unique()
            for comment_id in comment_ids:
                answer_comment_voters.extend(self._comment_voters(comment_id))

        content = answer_givers + question_commentators + answer_comentators
        voters = question_voters + question_comment_voters + answer_voters + answer_comment_voters
        all = content + voters

        return all, content, voters
