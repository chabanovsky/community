import os
import csv
import sys
import re

import pandas as pd
import numpy as np
import scipy.stats as stats
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import math

from __future__ import print_function
from IPython.display import HTML
import pylab as pl

from bokeh.io import show
from bokeh.models import ColumnDataSource, FactorRange
from bokeh.plotting import figure
from bokeh.transform import factor_cmap
from bokeh.palettes import Spectral5
from bokeh.settings import convert_str

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
    def __init__(self, spreadsheet_id, db_name, questions_in_the_series, project_path_prefix=project_path_prefix):
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

class QuestionVisualFeedback:
    def __init__(self, question_id, data):
        self.question_id = question_id
        self.all_data = data
        self.q_data = data.all_feedback[data.all_feedback["ParentId"] == question_id]

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

class SeriesVisualization:
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