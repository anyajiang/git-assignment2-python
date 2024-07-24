from shiny import App, reactive, render, req, ui, Inputs, Outputs, Session 
import rpy2 
import rpy2.robjects as ro
import rpy2.robjects.packages as rpackages
from rpy2.robjects.vectors import StrVector
from rpy2.robjects.packages import importr
from rpy2.robjects import pandas2ri
import os
import pyreadr
from rpy2.robjects import pandas2ri
import pandas as pd
import numpy as np
import io



pandas2ri.activate()

utils = rpackages.importr('utils')
utils.chooseCRANmirror(ind=1)
packnames = ('Seurat')
utils.install_packages(StrVector(packnames))
path="/Users/anyajiang/Desktop/pythonassignment2/"

os.environ["OPENAI_API_KEY"] = "XXXXXX"


app_ui = ui.page_fluid(
    ui.layout_sidebar(
        ui.panel_sidebar(
            ui.h2("GPTCelltype Annotation"), 
            ui.input_selectize("dataset","Select Input Data Format", choices = ("Input Gene List", "Differential Gene Table"), selected = "Input Gene List", multiple = False),
            ui.panel_conditional(
                "input.dataset == 'Input Gene List'", 
                ui.input_text_area("gene_list", "Enter Gene List", rows = 5), 
                ui.input_action_button("example", "Example Query")
            ), 
            ui.panel_conditional(
                "input.dataset == 'Differential Gene Table'", 
                ui.input_file("file", "Upload Markers File")
            ),
            ui.input_selectize("model", label = "Select Model", choices = ("gpt-4o", "gpt-4", "gpt-3.5-turbo"), selected = "gpt-4o", multiple = False),
            ui.input_action_button("annotate", "Annotate Cell Type")
        ), 
        ui.panel_main(
            ui.h3("Cell Type Annotation: "), 
            ui.panel_conditional(
                "input.dataset == 'Input Gene List'", 
                ui.output_ui("dynamic_ui1")
            ), 
            ui.panel_conditional(
                "input.dataset == 'Differential Gene Table'", 
                ui.output_ui("dynamic_ui2")
            )
        )
    )
)

def server(input, output, session):

    def gptcelltype(input):
        r=ro.r
        r.source(path+"gptcelltype.R")
        p=r.gptcelltype(input)
        return p

    @reactive.effect
    @reactive.event(input.annotate)
    def _(): 

        if input.dataset() == 'Input Gene List':
            gene_groups = input.gene_list().split("\n")
            input_list = list(map(str.split, gene_groups))

            result = gptcelltype(input=input_list)
            
            res_table = {
                "Group": [f"Group{i+1}" for i in range(len(input_list))],
                "Genes": [" ".join(group) for group in input_list],
                "Cell_Type": result
            }

            df = pd.DataFrame(res_table)
            df = df.style.set_properties(**{'text-align': 'left'}).hide(axis='index')
        
            
            @output
            @render.ui
            def dynamic_ui1():
                return ui.TagList(
                    ui.output_table("table"),
                    ui.download_button("download_table", "Download")
                )
            
            @output
            @render.table
            def table():
                return df
            
            @render.download(filename = "gene_list_table.csv")
            def download_table():
                df = pd.DataFrame(res_table)
                yield df.to_csv()

            
           
            
        elif input.dataset() == 'Differential Gene Table': 
            file_info = req(input.file())
            file_path = file_info[0]['datapath']
            
            readRDS = ro.r['readRDS']
            df = readRDS(file_path)
            
            df = pandas2ri.py2rpy(df)
            input_list = df
            
            results = gptcelltype(input=input_list)

            res_table = pd.DataFrame({
                "Group": [f"Group{i+1}" for i in range(len(results))],
                "Cell_Type": results
            })

            df = pd.DataFrame(res_table) 
            df = df.style.set_properties(**{'text-align': 'left'}).hide(axis='index')

            @output
            @render.ui
            def dynamic_ui2():
                return ui.TagList(
                    ui.output_table("table2"),
                    ui.download_button("download_table2", "Download")
                )
            
            @render.table
            def table2():
                return df     

            @session.download(filename = "differential_gene_table.csv")
            def download_table2():
                df = pd.DataFrame(res_table)
                yield df.to_csv()


            
    @reactive.effect
    @reactive.event(input.example)
    def _(): 
        ui.update_text_area("gene_list", value = "CD4 CD3D \n CD14")


app = App(app_ui, server)

