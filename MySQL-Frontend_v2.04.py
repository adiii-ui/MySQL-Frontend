import sys
from PyQt5.uic import loadUi
from PyQt5 import QtWidgets, QtCore, QtGui

from PyQt5.QtWidgets import QFileDialog, QDialog, QApplication, QMessageBox, QTableWidgetItem, QAbstractItemView, QInputDialog
import mysql.connector as sql
import time

import csv, os  # used by selectiveDisplay_table() to export the output as CSV

#==== global variables ====
myconn=None  # MySQL Connection !! VVImp !!
mycur=None	 # MySQL Connection Cursor
login_status=False
DB_list=[]
TB_list=[]
DB_TB_choice=[]#carries selected DB and TB !! VVImp !!
TB_Col_choice=[None,None] # carries selected TB and Column(s) for selective display
usr_data=[] #carries user login info
queryended=False # -> bool
set_as_primarykey=False # -> bool
primary_key_exists=None # -> bool (for update function)
final_query='' # -> str
renamed_DB=None # -> str -value is the name of the renamed database
col_TBD=None  #column to be deleted -> str
col_TBM=None #column to be modified -> str
col_TBR=[None,None] #column to be renamed [<new_name>, <datatype>]
delete_data_action=None # data to be deleted...
                        #	- if delete all data is enabled, this var will carry a str "ALL"
                        #	- if delete one row is enabled, this var will carry all necessary info of the selected row
update_table_query_lst=[]
# list that carries all updation queries for execution.
updated_DATA = False # [bool] value becomes true if all table_data updated successfully

#  |----\   /-----\  |----\   |     |  |----\    /-----
#  |     \  |     |  |     \  |     |  |     \  | 
#  |-----/  |     |  |-----/  |     |  |-----/  |-----|
#  |        |     |  |        |     |  |              |
#  |        \-----/  |         \---/   |        -----/




class delete_db_confirmation(QDialog):
    def __init__(self,parent=None):
        super(delete_db_confirmation,self).__init__()
        loadUi("delete_DB_confirmation.ui",self)
        self.buttonBox.accepted.connect(self.deleteDB)
        
        
    def deleteDB(self):
        time.sleep(1)
        global DB_TB_choice, myconn, mycur
        query="drop database {}".format(DB_TB_choice[0])
        try:
            mycur.execute(query)
            myconn.commit()
            msg="Database was deleted successfully."
            popup=QMessageBox.about(self,'Success',msg)
            DB_TB_choice[0]=None
        except Exception as E:
            ERROR=str(E)
            msg="ERROR: {}".format(ERROR.upper())
            popup=QMessageBox.about(self,'INTERNAL ERROR',msg)

class delete_data_confirmation(QDialog):
    def __init__(self,parent=None):
        super(delete_data_confirmation,self).__init__()
        loadUi("delete_DATA.ui",self)
        self.fetch_DATA()
       
        self.chk_for_primaryKey()
        self.del_oneRow.toggled.connect(self.setSelection_oneRow)
        self.del_wholeTB_DATA.toggled.connect(self.setSelection_ALL)
        self.next.clicked.connect(self.goFwd)
        self.previous.clicked.connect(lambda:self.stackedWidget.setCurrentIndex(self.stackedWidget.currentIndex() - 1))
        self.selectedTB.setText(DB_TB_choice[1])
        
        self.tableWidget.itemClicked.connect(self.display_selectedRow)
        self.YES.clicked.connect(self.determine_del_action)
        self.NO.clicked.connect(lambda:self.reject()) 
        
    def display_selectedRow(self):
       
        row_index=self.tableWidget.currentRow()
        if row_index == 0:
            self.selectedRow.setText('Selected Row: 0 [UNACCEPTABLE VALUE!]')
        else:
            self.selectedRow.setText("Selected Row: {}".format(row_index))
    
    def chk_for_primaryKey(self):
        global DB_TB_choice, myconn, mycur
        try:   # searches for primary key in the table
            query="desc {}".format(DB_TB_choice[1])
            mycur.execute(query)
            rs=mycur.fetchall()
            for row in rs:
                if row[3] == 'PRI':
                    self.del_oneRow.setEnabled(True)
                    self.tableWidget.setEnabled(True)
                    break
            else:
                self.del_oneRow.setEnabled(False)
                self.tableWidget.setEnabled(False)
                self.del_wholeTB_DATA.setChecked(True)
                self.selectedRow.setText('No Primary key found. So only truncate table allowed.')
                    
            
        except Exception as E:
            msg="ERROR: {}".format(str(E)) + "\nType: {}".format(str(type(E)))
            print(msg)
            popup=QMessageBox.about(self,'ERROR - Check for PRI FAIL',msg)
            
    
    def setSelection_oneRow(self):
        row_index=self.tableWidget.currentRow()
        self.selectedRow.setText("Selected Row: {}".format(row_index))
        self.tableWidget.setEnabled(True)
        self.tableWidget.setSelectionMode(QAbstractItemView.SingleSelection)
    
    def determine_del_action(self):
        global delete_data_action
        try:
            if type(delete_data_action) is int:  # carries row index to be deleted
                self.deleteRow()
            elif type(delete_data_action) is str and delete_data_action == "ALL" : # 
                self.deleteALL_DATA()
        except Exception as E:
            msg="DELETE() DETERMINATION ERROR: {}".format(str(E)) + "\nType: {}".format(str(type(E)))
            popup=QMessageBox.about(self,'DETERMINATION ERROR',msg)
    
    def setSelection_ALL(self):
        self.selectedRow.setText('')
        self.tableWidget.setEnabled(False)
     
     
    def fetch_DATA(self):
        global DB_TB_choice, myconn, mycur
        TB=DB_TB_choice[1]
        try:
            time.sleep(1)
            column_names=[]
            columncount=None
            query1="desc {}".format(TB)
            mycur.execute(query1)
            rs1=mycur.fetchall()
            count1=mycur.rowcount
            if rs1 == []:
                msg="Nothing is saved in this table"
                popup=QMessageBox.about(self,'Alert',msg)
                exit
            else:
                for row in rs1:
                    column_names.append(row[0])    
            
                query2="select * from {}".format(TB)
                mycur.execute(query2)
                rs2=mycur.fetchall()
                if rs2 == []:
                    msg="No data is saved in this table."
                    popup=QMessageBox.about(self,'Alert',msg)
                    exit
                else:
                    rowcount=mycur.rowcount
            
                    for row in rs2:
                        columncount=len(row)
           
                    self.tableWidget.setRowCount(rowcount+1)
                    self.tableWidget.setColumnCount(columncount+1)
                    self.tableWidget.setItem(0,0,QTableWidgetItem("Sl.No"))
                    self.tableWidget.item(0,0).setBackground(QtGui.QColor(191,239,239))
                    i=0
                    for column_name in column_names:
                        i+=1
                        self.tableWidget.setItem(0,i,QTableWidgetItem(column_name))
                        self.tableWidget.item(0,i).setBackground(QtGui.QColor(191,239,239))
                                                                              
                    for r_i in range(1, rowcount+1):
                        self.tableWidget.setItem(r_i,0,QTableWidgetItem(str(r_i)))
                        for c_i in range(1, columncount+1):
                            self.tableWidget.setItem(r_i,c_i,QTableWidgetItem(str(rs2[r_i - 1][c_i - 1])))
                
            
        except Exception as E:
            msg = "delete() fetchDATA() Error: {}".format(str(E)) + "\nType: {}".format(type(E))
            print(msg,'\a')
            popup=QMessageBox.about(self,'ERROR',msg)
    
    def goFwd(self):
        global delete_data_action
        if self.del_oneRow.isChecked():
            row_index=self.tableWidget.currentRow()
            print('row_index =',row_index)
            if row_index == None or row_index == 0:
                popup=QMessageBox.about(self,"Error","Please select one row to proceed.\nTopmost row cannot be deleted.\nCheck again.")
            else:
                delete_data_action=row_index
                self.stackedWidget.setCurrentIndex(self.stackedWidget.currentIndex() + 1)
                self.del_action_label.setText("row number '{}' from the table?".format(row_index))
        elif self.del_wholeTB_DATA.isChecked():
            delete_data_action='ALL'
            self.stackedWidget.setCurrentIndex(self.stackedWidget.currentIndex() + 1)
            self.del_action_label.setText("ALL ROWS from the table?")
            
    def deleteALL_DATA(self):
        time.sleep(1.5)
        self.accept()  # closes deletes all the saved data on the table
        global DB_TB_choice, myconn, mycur, delete_data_action
        try:
            query="truncate table {}".format(DB_TB_choice[1])
            mycur.execute(query)
            myconn.commit()
            popup=QMessageBox.about(self," Deletion Success","The table '{}' was truncated successfully.".format(DB_TB_choice[1]))
            print("\aThe table '{}' got truncated.".format(DB_TB_choice[1]))
        except Exception as E:
            msg="ERROR: {}".format(str(E)) + "\nType: {}".format(str(type(E)))
            popup=QMessageBox.about(self,'DELETION ERROR (1)',msg)
            
        
    def deleteRow(self):
        self.accept()
        time.sleep(1.5)
        global DB_TB_choice, myconn, mycur, delete_data_action
        row_index=delete_data_action
        # checks if primary key exists
        primary_key_exists=None
        primary_key=None
        primary_key_DT=None
       
        try:   # searches for primary key in the table
            query="desc {}".format(DB_TB_choice[1])
            mycur.execute(query)
            rs=mycur.fetchall()
            for row in rs:
                if row[3] == 'PRI':
                    primary_key_exists=True
                    primary_key=str(row[0])  #saves name of primary key
                    primary_key_DT=row[1] # saves datatype of primary key
                 
                    break
            else:
                primary_key_exists=False
        except Exception as E:
            msg="ERROR: {}".format(str(E)) + "\nType: {}".format(str(type(E)))
            print(msg)
            popup=QMessageBox.about(self,'DELETION ERROR (2 - Check for PRI FAIL)',msg)
            
        
        if primary_key_exists==True:
            primary_key_value=None
            column_count=self.tableWidget.columnCount()
            for i in range(column_count):
                if self.tableWidget.item(0,i).text() == primary_key:
                    primary_key_value=primary_key_value= self.tableWidget.item(row_index,i).text()  #accounting for serial no column
                    break 
            try:
                if primary_key_DT[:4] == 'char'  or primary_key_DT.lower() == 'date':
                    last_query="delete from {} where {} = '{}'".format(DB_TB_choice[1],primary_key,primary_key_value)
                else:
                    last_query="delete from {} where {} = {}".format(DB_TB_choice[1],primary_key,primary_key_value)
                mycur.execute(last_query)
                myconn.commit()
                popup=QMessageBox.about(self,"Success","The row was deleted.")
                print("A row got deleted.")
            except Exception as E:
                msg="Error: {}".format(str(E)) + "\nType: {}".format(str(type(E)))
                print(msg)
                popup=QMessageBox.about(self,'DELETION ERROR (2 - EXECUTION FAIL)',msg)
            
            
        else:
            msg="ERROR: Primary Key is not found!!"
            print(msg)
            popup=QMessageBox.about(self,'MISSING PRIMARY KEY (2)',msg) 
            
            
        



class delete_tb_confirmation(QDialog):
    def __init__(self,parent=None):
        super(delete_tb_confirmation,self).__init__()
        loadUi("delete_TB_confirmation.ui",self)
        self.buttonBox.accepted.connect(self.deleteTB)
    
    def deleteTB(self):
        time.sleep(1)
        global DB_TB_choice, myconn, mycur
        query="drop table {}".format(DB_TB_choice[1])
        try:
            mycur.execute(query)
            myconn.commit()
            msg="Table was deleted successfully."
            popup = QMessageBox.about(self,'Success',msg)
            DB_TB_choice[1]=None
        except Exception as E:
            ERROR=str(E)
            msg="ERROR: {}".format(ERROR.upper())
            popup=QMessageBox.about(self,'INTERNAL ERROR',msg)


class delete_Column_confirmation(QDialog):
    def __init__(self,parent=None):
        super(delete_Column_confirmation,self).__init__()
        loadUi("delete_col_confirmation.ui",self)
        self.buttonBox.accepted.connect(self.deleteColumn)
        self.next.clicked.connect(self.goFwd)
        self.fetchColumns()
        self.previous.clicked.connect(self.goBack)
        self.col_listWidget.itemDoubleClicked.connect(self.getColumn)
    
    def goBack(self):
        self.stackedWidget.setCurrentIndex(self.stackedWidget.currentIndex() - 1)
    
    def goFwd(self):
        global col_TBD
        if col_TBD == None:
            self.alert_label.setText("Can't delete an unspecified column.")
        else:
            self.alert_label.setText("")
            self.stackedWidget.setCurrentIndex(self.stackedWidget.currentIndex() + 1)
    
    def getColumn(self):
        global col_TBD
        item=self.col_listWidget.currentItem()
        col_TBD=item.text()
        self.selected_col.setText("Selected: {}".format(col_TBD))
        self.Cselected_col.setText("Selected: {}".format(col_TBD))
        
    
    def fetchColumns(self):
        global DB_TB_choice, myconn, mycur
        try:
            query="desc {}".format(DB_TB_choice[1])
            mycur.execute(query)
            rs=mycur.fetchall()
            if rs == []:
                msg="No column found to delete in this table."
                popup=QMessageBox.about(self,"Alert",msg)
                print('\a',msg)
            else:
                for row in rs:
                    self.col_listWidget.addItem(row[0])
                print('Fetched all Columns.')
        except Exception as E:
            Msg="Error: {}".format(str(E))
            popup=QMessageBox.about(self,"INITIALIZATION ERROR",msg)
            print(msg,'\n\a')
    
    def deleteColumn(self):
        global DB_TB_choice, myconn, mycur, col_TBD
        try:
            query="alter table {} drop {}".format(DB_TB_choice[1],col_TBD)
            mycur.execute(query)
            myconn.commit()
            msg="The column is now unretrievable history ;)"
            popup=QMessageBox.about(self,"Column Deleted!",msg)
            col_TBD=None
            print("A column from the table {} just got deleted.".format(DB_TB_choice[1]))
        except Exception as E:
            msg="Error: {}".format(str(E))
            popup=QMessageBox.about(self,'ERROR',msg)

class rename_tb_confirmation(QDialog):
    def __init__(self,parent=None):
        super(rename_tb_confirmation,self).__init__()
        loadUi("rename_TB_confirmation.ui",self)
        self.next.clicked.connect(self.goFwd)
        self.previous.clicked.connect(self.goBack)
        self.buttonBox.accepted.connect(self.renameTB)
        self.existing_TB.setText(str(DB_TB_choice[1]))
    
    def goFwd(self):
        newTB_name=self.renameTB_textbox.text()
        if len(newTB_name) == 0:
            msg='Please enter a new name for table.'
            popup=QMessageBox.about(self,'Incomplete Field',msg)
        else:
            self.stackedWidget.setCurrentIndex(self.stackedWidget.currentIndex() + 1)
            
    def goBack(self):
        self.stackedWidget.setCurrentIndex(self.stackedWidget.currentIndex() - 1)
            
    def renameTB(self):
        newTB_name=self.renameTB_textbox.text()
        time.sleep(1)
        global DB_TB_choice, myconn, mycur
        query="rename table {} to {}".format(DB_TB_choice[1],newTB_name)
        try:
            mycur.execute(query)
            myconn.commit()
            msg="Table was renamed successfully."
            popup = QMessageBox.about(self,'Success',msg)
            DB_TB_choice[1]=None
        except Exception as E:
            ERROR=str(E)
            msg="ERROR: {}".format(ERROR.upper())
            popup=QMessageBox.about(self,'INTERNAL ERROR',msg)

class rename_Col_confirmation(QDialog):
    def __init__(self,parent=None):
        global DB_TB_choice, col_TBR
        super(rename_Col_confirmation,self).__init__()
        loadUi("rename_col_confirmation.ui",self)
        self.fetchColumns()
        self.selectedTB.setText("Selected Table: {}".format(DB_TB_choice[1]))
        self.col_listWidget.itemClicked.connect(self.selectColumn)
        self.next.clicked.connect(self.goFwd)
        self.previous.clicked.connect(self.goBack)
        self.buttonBox.accepted.connect(self.renameCOLUMN)
        
    
    def selectColumn(self):
        global DB_TB_choice, col_TBR, myconn, mycur
        item=self.col_listWidget.currentItem()
        Column=item.text()
        col_TBR[0]=Column
        print("Got selected column.")
        self.selected_Col.setText(col_TBR[0])
        try:
            query="desc {}".format(DB_TB_choice[1])
            mycur.execute(query)
            rs=mycur.fetchall()
            for row in rs:
                if row[0]==col_TBR[0]:
                    col_TBR[1]=row[1]
                    break
            print("Got selected column datatype")
        except Exception as E:
            msg="ERROR: {}\nTYPE:{}" .format(str(E),type(E))
            popup=QMessageBox.about(self,"INITIALIZATION ERROR",msg)
            
    def goFwd(self):
        global col_TBR
        if col_TBR[0] == None and self.renameCol_textBox.text() == '':
            popup=QMessageBox.about(self,"Error","No Column is Selected.\nNo name is entered.")
            print("\aNo Column is Selected.\nNo name is entered.")
            return
        else:
            if col_TBR[0] == None:
                popup=QMessageBox.about(self,"Error","No Column is Selected.")
                print("\aNo Column is Selected.")
                return
            if self.renameCol_textBox.text() == '':
                popup=QMessageBox.about(self,"Error","No name is entered.")
                print("\aNo name is entered.")
                return
            else:
                self.stackedWidget.setCurrentIndex(self.stackedWidget.currentIndex() + 1)
                self.old_name_label.setText(col_TBR[0])
                self.new_name_label.setText(self.renameCol_textBox.text())
                self.buttonBox.setEnabled(True)
    
    def goBack(self):
        self.stackedWidget.setCurrentIndex(self.stackedWidget.currentIndex() - 1)
    
        
    def renameCOLUMN(self):
        global DB_TB_choice, myconn, mycur, col_TBR
        new_name=self.renameCol_textBox.text()
        try:
            query="alter table {} change {} {} {}".format(DB_TB_choice[1],col_TBR[0],new_name,col_TBR[1])
            print(query)
            mycur.execute(query)
            myconn.commit()
            msg="The column was renamed successfully."
            popup=QMessageBox.about(self,"Success",msg)
        except Exception as E:
            popup=QMessageBox.about(self,"Error","ERROR: {}\nTYPE: {}".format(str(E),type(E)))
            self.reject()
       
        
        
    def fetchColumns(self):
        global DB_TB_choice, myconn, mycur
        try:
            query="desc {}".format(DB_TB_choice[1])
            mycur.execute(query)
            rs=mycur.fetchall()
            if rs == []:
                msg="No column found to delete in this table."
                popup=QMessageBox.about(self,"Alert",msg)
                print('\a',msg)
            else:
                for row in rs:
                    self.col_listWidget.addItem(row[0])
                print('Fetched all Columns.')
        except Exception as E:
            Msg="Couldn't fetch columns." + "\nError: {}".format(str(E))
            popup=QMessageBox.about(self,"INITIALIZATION ERROR",msg)
            print(msg,'\n\a')

class display_table(QDialog):
    def __init__(self,parent=None):
        global DB_TB_choice
        super(display_table,self).__init__()
        loadUi("display_TB.ui",self)
        self.exit.clicked.connect(self.close_popup)
        self.label.setText("Table '{}'".format(DB_TB_choice[1]))
        self.fetch_DATA()
    
    def close_popup(self):
        print('Closed.')
        self.reject()
    
    def fetch_DATA(self):
        global DB_TB_choice, myconn, mycur
        
        try:
            TB=DB_TB_choice[1]
            time.sleep(1)
            column_names=[]
            columncount=None
            query1="desc {}".format(TB)
            mycur.execute(query1)
            rs1=mycur.fetchall()
            count1=mycur.rowcount
            if rs1 == []:
                msg="Nothing is saved in this table"
                popup=QMessageBox.about(self,'Alert',msg)
                exit
            else:
                for row in rs1:
                    column_names.append(row[0])    
            
                query2="select * from {}".format(TB)
                mycur.execute(query2)
                rs2=mycur.fetchall()
                if rs2 == []:
                    msg="No data is saved in this table.\nTo view this table's attributes, hit the 'Describe Table' button."
                    popup=QMessageBox.about(self,'Alert',msg)
                    exit
                else:
                    rowcount=mycur.rowcount
            
                    for row in rs2:
                        columncount=len(row)
           
                    self.tableWidget.setRowCount(rowcount+1)
                    self.tableWidget.setColumnCount(columncount+1)
                    self.tableWidget.setItem(0,0,QTableWidgetItem("Sl.No"))
                    self.tableWidget.item(0,0).setBackground(QtGui.QColor(191,239,239))
                    i=0
                    for column_name in column_names:
                        i+=1
                        self.tableWidget.setItem(0,i,QTableWidgetItem(column_name))
                        self.tableWidget.item(0,i).setBackground(QtGui.QColor(191,239,239))
                                                                              
                    for r_i in range(1, rowcount+1):
                        self.tableWidget.setItem(r_i,0,QTableWidgetItem(str(r_i)))
                        for c_i in range(1, columncount+1):
                            self.tableWidget.setItem(r_i,c_i,QTableWidgetItem(str(rs2[r_i - 1][c_i - 1])))
                
            
        except Exception as E:
            msg = "Error: {}".format(str(E)) + "\nType: {}".format(type(E))
            print(msg,'\a')
            popup=QMessageBox.about(self,'ERROR',msg)

class selectiveDisplay_table(QDialog):
    appendedColumns=[]
    column_names=[]
    def __init__(self,parent=None):
        global DB_TB_choice, TB_Col_choice
        TB_Col_choice=[None,None]
        super(selectiveDisplay_table,self).__init__()
        loadUi("selectiveDisplay_TB.ui",self)
        self.fetchColumns()
        self.fetchTB()
        self.goback.clicked.connect(lambda:self.stackedWidget.setCurrentIndex(self.stackedWidget.currentIndex() - 1))
        self.Querybox.textCursor().insertText("select * from {}".format(DB_TB_choice[1]))
        self.clear_query.clicked.connect(self.clearQuery)
        self.executor.clicked.connect(self.execute)
        self.TB_listWidget.itemDoubleClicked.connect(self.fetchColumns)
        self.col_listWidget.itemDoubleClicked.connect(lambda:self.selected_Col.setText(self.col_listWidget.currentItem().text()))
        self.append_tb.clicked.connect(self.setTB)
        self.append_col.clicked.connect(self.setCol)
        self.selectedTB.setText(DB_TB_choice[1])
        self.exit.clicked.connect(lambda:self.reject())
        self.exit_2.clicked.connect(lambda:self.reject())
        self.supportedQueries.clicked.connect(self.launchSupportedQueryDialog)
        self.clear_buffer.clicked.connect(lambda:selectiveDisplay_table.appendedColumns.clear())
        self.exportToCSV.clicked.connect(self.export_output_to_CSV)
        self.query_listWidget.itemDoubleClicked.connect(self.reInsertQuery)

    def clearQuery(self):
        query=self.Querybox.toPlainText()
        for item_index in range(self.query_listWidget.count()):
            if self.query_listWidget.item(item_index).text() == query:
                break
        else:
            self.query_listWidget.addItem(query)
        self.Querybox.clear()

    def export_output_to_CSV(self):
        defaultFilename = 'MySQL_DataExport'
        i = 0
        while True:
            try:
                if i == 0:
                    csvFile=open(defaultFilename + '.csv','x')
                    break
                else:
                    defaultFilename = 'MySQL_DataExport'
                    defaultFilename += "({})".format(i)
                    csvFile=open(defaultFilename + '.csv','x')
                    break
            except Exception:
                i+=1
                continue
        csvFile.close()
        os.remove(defaultFilename + '.csv')



        COLUMNS = []
        DATA = [] 
        row_count = self.tableWidget.rowCount()
        col_count = self.tableWidget.columnCount()
        #fetch_DaTA
        for row_index in range(1,row_count):
            rowDATA = []
            for col_index in range(1,col_count):
                if self.tableWidget.item(row_index,col_index).text().upper() == 'NONE':
                    rowDATA.append(None)
                else:
                    rowDATA.append(self.tableWidget.item(row_index,col_index).text())
            DATA.append(rowDATA)
        #fetch_Columns
        COLUMNS = selectiveDisplay_table.column_names
               
        print('exportToCSV() COLUMNS:',COLUMNS)
        print('exportToCSV() DATA:',DATA)
        option = QFileDialog.Options()
        #option |= QFileDialog.DontUseNativeDialog
        fileName_tup = QFileDialog.getSaveFileName(self,"Save CSV File",defaultFilename + '.csv','CSV Files (*.csv)',options= option)

        print('Obtained Filename:',fileName_tup)
        fileName = fileName_tup[0]
        if fileName != '':
            csvFile=open(fileName,'w')
            csvWriter = csv.writer(csvFile)
            csvWriter.writerow(COLUMNS)
            csvWriter.writerows(DATA)
            csvFile.close()
            self.fileSave.setText('File Saved Succesfully!')
        else:
            return



    def launchSupportedQueryDialog(self):
        dialog=supportedQueries()
        if dialog.exec():
            return
     
    def reInsertQuery(self,item):
        query = item.text()
        self.Querybox.clear()
        self.Querybox.append(query)
        
    
    def setTB(self):
        self.Querybox.clear()
        global TB_Col_choice
        TB=self.TB_listWidget.currentItem().text()
        TB_Col_choice[0]=TB
        self.selectedTB.setText(TB)
        self.fetchColumns()
        TB_Col_choice[1]=None
        self.Querybox.append("select * from {}".format(TB_Col_choice[0]))
        
                
    def getCol(self):
        columns=selectiveDisplay_table.appendedColumns
        items=self.col_listWidget.selectedItems()
        for each_item in items:
            columns.append(each_item.text())
        print('getCOL() COLUMNS:',columns)
        selectiveDisplay_table.appendedColumns=columns

        
    def setCol(self):
        global TB_Col_choice, DB_TB_choice
        TB = TB_Col_choice[0]
        self.getCol()
        self.Querybox.clear()
        columns=selectiveDisplay_table.appendedColumns
        print('SETCOL() columns:',columns)
        columns_str=''
        if TB==None:
            for each_column in columns:
                columns_str += each_column + ' ,'
            columns_str=columns_str[:-1]
            self.Querybox.append("select {} from {}".format(columns_str,DB_TB_choice[1]))
            self.selected_Col.setText(columns_str)
        else:
            
            for each_column in columns:
                columns_str += each_column + ' ,'
            columns_str = columns_str[:-1]
            self.Querybox.append("select {} from {}".format(columns_str,TB_Col_choice[0]))
            self.selected_Col.setText(columns_str)
            
        
    
    def fetchTB(self):
        self.TB_listWidget.clear()
        global mycur, TB_list
        try:
            query2 = 'show tables'
            mycur.execute(query2)
            rs=mycur.fetchall()
            for row in rs:
                TB_list.append(row[0])
                self.TB_listWidget.addItem(row[0])
        except Exception as E:
            msg="ERROR: " + str(E)
            popup=QMessageBox.about(self,"INTERNAL ERROR",msg)
            print("\aERROR: " + str(E))
    
    def fetchColumns(self):
        
        if self.TB_listWidget.currentItem() != None:
            TB_Col_choice[0] = self.TB_listWidget.currentItem().text()

        self.col_listWidget.clear()
        global DB_TB_choice,TB_Col_Choice, myconn, mycur
        try:
            if TB_Col_choice[0]==None:
                query="desc {}".format(DB_TB_choice[1])
            else:
                query="desc {}".format(TB_Col_choice[0])
            mycur.execute(query)
            rs=mycur.fetchall()
            if rs == []:
                msg="No column found in this table."
                popup=QMessageBox.about(self,"Alert",msg)
                print('\a',msg)
                return
            else:
                for row in rs:
                    self.col_listWidget.addItem(row[0])
                print('Fetched all Columns.')
        except Exception as E:
            Msg="fetchCOLUMNS(): Couldn't fetch columns." + "\nError: {}".format(str(E))
            popup=QMessageBox.about(self,"__INIT__ ERROR",msg)
            print(msg,'\n\a')
    

    def execute(self):
        global myconn, mycur
        query=self.Querybox.toPlainText()
        if len(query) == 0:
            popup = QMessageBox.about(self,'EMPTY QUERYBOX',"QueryBox cannot be empty.")
            print('\a')
        else:
            
           
            try:
                
                mycur.execute(query)
                rs2=mycur.fetchall()
                if rs2 == []:
                    msg="No data could be fetched! Check your query and retry."
                    popup=QMessageBox.about(self,'Alert',msg)
                    return
                else:
                    rowcount=mycur.rowcount
                    columncount=len(rs2[0])
            

           
                    self.tableWidget.setRowCount(rowcount+1)
                    self.tableWidget.setColumnCount(columncount+1)
                    self.tableWidget.setItem(0,0,QTableWidgetItem("Sl.No"))
                    self.tableWidget.item(0,0).setBackground(QtGui.QColor(191,239,239))
                    i=0
                                     
                
                    column_names=mycur.column_names
                    selectiveDisplay_table.column_names = column_names
                    for column_name in column_names:
                        i+=1
                        self.tableWidget.setItem(0,i,QTableWidgetItem(column_name))
                        self.tableWidget.item(0,i).setBackground(QtGui.QColor(191,239,239))
                       
                            
                   
                    
                                                                              
                    for r_i in range(1, rowcount+1):
                        self.tableWidget.setItem(r_i,0,QTableWidgetItem(str(r_i)))
                        for c_i in range(1, columncount+1):
                            self.tableWidget.setItem(r_i,c_i,QTableWidgetItem(str(rs2[r_i - 1][c_i - 1])))
                self.stackedWidget.setCurrentIndex(self.stackedWidget.currentIndex() + 1)
                
                
            
            except Exception as E:
                msg = "Error: {}".format(str(E)) + "\nType: {}".format(type(E))
                print(msg,'\a')
                popup=QMessageBox.about(self,'ERROR',msg)
                
class supportedQueries(QDialog):
    def __init__(self):
        super(supportedQueries,self).__init__()
        loadUi('supportedQueriesDialog.ui',self)
        self.buttonBox.accepted.connect(lambda:self.accept())
     
        






class desc_table(QDialog):
    def __init__(self,parent=None):
        global DB_TB_choice
        super(desc_table,self).__init__()
        loadUi("display_TB.ui",self)
        self.exit.clicked.connect(self.close_popup)
        self.setWindowTitle("Table Description")
        self.label.setText("Description of Table '{}'".format(DB_TB_choice[1]))
        self.fetch_DATA()
    
    def close_popup(self):
        print('Closed.')
        self.reject()
    
    def fetch_DATA(self):
        global DB_TB_choice, myconn, mycur
        TB=DB_TB_choice[1]
        rs=[]
        try:
            query="desc {}".format(TB)
            mycur.execute(query)
            rs=mycur.fetchall()
            rowCount=mycur.rowcount
            columnCount=None
            #print('GOT ATTRIB METADATA.')
            for row in rs:
                print(row)
                columnCount=len(row)
            self.tableWidget.setRowCount(rowCount+1)
            self.tableWidget.setColumnCount(columnCount+1)
            
            self.tableWidget.setItem(0,0,QTableWidgetItem("Sl No"))
            self.tableWidget.setItem(0,1,QTableWidgetItem("Attribute Name"))
            self.tableWidget.setItem(0,2,QTableWidgetItem("DataType"))
            self.tableWidget.setItem(0,3,QTableWidgetItem("Null allowed?"))
            self.tableWidget.setItem(0,4,QTableWidgetItem("Key"))
            self.tableWidget.setItem(0,5,QTableWidgetItem("Default"))
            self.tableWidget.setItem(0,6,QTableWidgetItem("Extra"))
           
             
            for r in range(rowCount):
                self.tableWidget.setItem(r+1,0,QTableWidgetItem(str(r+1)))
               # self.Attrib_table.setItem(r+1,6,QTableWidgetItem("End of Row"))
            for r_i in range(1,rowCount+1):
                for c_i in range(1,columnCount):
                    item=QTableWidgetItem(str(rs[r_i-1][c_i-1]))
                    self.tableWidget.setItem(r_i,c_i,item)
            for j in range(columnCount+1):
                self.tableWidget.item(0,j).setBackground(QtGui.QColor(191,239,239))
                    
            self.tableWidget.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers) # B  I  G      B  R  A  I  N
            
        except Exception as E:
            msg="ERROR: {}".format(str(E))
            popup=QMessageBox.about(self,'INTERNAL ERROR 1',msg)
            #self.reject()



class rename_db_confirmation(QDialog):
    def __init__(self,parent=None):
        global DB_TB_choice
        super(rename_db_confirmation,self).__init__()
        loadUi("rename_DB_confirmation.ui",self)
        self.buttonBox.accepted.connect(self.renameDB)
    
    def renameDB(self):
        global DB_TB_choice, myconn, mycur, final_query
        time.sleep(1)
        
        query="use {}".format(DB_TB_choice[0])
        mycur.execute(query)
        tb_list=[]
        time.sleep(1)
        query_="show tables"
        mycur.execute(query_)
        r_s=mycur.fetchall()
        if r_s == []:
            popup=QMessageBox.about(self,'Error 3','Error: No Saved Tables found!\nRequired at least one saved table in this database for the rename function to work.')
            exit
        else: 
            try:
                query_1="create database {}".format(renamed_DB)
                mycur.execute(query_1)        
                myconn.commit()
                time.sleep(1)
            except Exception as E:
                popup=QMessageBox.about(self,'Error 1','Error: ' + str(E))
                print(final_query)
                exit
            try:
                query_2="use {}".format(DB_TB_choice[0])
                mycur.execute(query_2)
                tb_list=[]
                time.sleep(1)
            except Exception as E:
                popup=QMessageBox.about(self,'Error 2','Error: ' + str(E))
                print(final_query)
                exit
            try:
                query_3="show tables"
                mycur.execute(query_3)
                rs=mycur.fetchall()
                for row in rs:
                    tb_list.append(row[0])
                final_query="rename table"
                for i in range(0,len(tb_list)):
                    final_query = final_query + " {}.{} to {}.{},".format(DB_TB_choice[0],tb_list[i],renamed_DB,tb_list[i])
                final_query = final_query[:-1:1] + " ;" 
                time.sleep(1)
                mycur.execute(final_query)
                myconn.commit()
                popup=QMessageBox.about(self,'Success',"DB {} has been renamed to {}.".format(DB_TB_choice[0],renamed_DB))
            except Exception as E:
                popup=QMessageBox.about(self,'Error 3','Error: ' + str(E))
                print(final_query)
                exit
            try:
                QUERY="DROP DATABASE {}".format(DB_TB_choice[0])
                mycur.execute(QUERY)
                myconn.commit()
                DB_TB_choice[0]=None
            except Exception as E:
                popup=QMessageBox.about(self,'Error 4','Error: ' + str(E))
                print(final_query)
                exit

class update_table_confirmation_querybox(QDialog):
    # this popup has 3 stackedWidget windows
	# first one is for displaying the generated update_table queries for editing and execution
	# second one is for displaying the generated insert_into_table_data queries for editing and execution
	# third one to display Warning if EXECUTE2_TEST() failed

    # there are 2 execution methods to execute queries to updateData in the selected table:
	# EXECUTE1(): for table(s) with a PRIMARY KEY
	#				Update is done by directly executing the update_table query using primaryKey as reference
	# EXECUTE2(): for table(s) WITHOUT a PRIMARY KEY
	# 				Update is done by 1st: TRUNCATE TABLE and 2nd: EXECUTE GENERATED insert_into_table_data Queries one_by_one
	#				function divided into 1. exeCUTE2_TEST(): EXECUTE GENERATED insert_into_table_data Queries one_by_one WITHOUT TRUNCATING DATA
	#									  2. exeCUTE2_FINAL(): EXECUTE GENERATED insert_into_table_data Queries one_by_one AFTER TRUNCATING DATA
	
	# this popup has 3 stackedWidget windows
	# first one is for displaying 
    primary_key_exists=None
    masterQuery='' # [str] main INSERT INTO TB query that will be executed for table(s) W/O PRIMARY KEY -- used for backup of queries
    masterQueryList = [] #[list] main INSERT INTO TB query saved individually, that will be executed for table(s) W/O PRIMARY KEY -- used for EXECUTE2()
    ACTIVE_QUERY='' # [str] main UPDATE TB query selected from Widget that will be executed for table(s) WITH PRIMARY KEY
    active_query_row = 0 #[int] carries row index of active query
    queryLst = [] # [list] to keep track of the individual update_data queries to be executed by user using exeCUTE1() method
    exec_all = False
    def __init__(self):
        super(update_table_confirmation_querybox,self).__init__()
        loadUi('update_TB_QUERIESDialog.ui',self)
        update_table_confirmation_querybox.primary_key_exists = self.chk_for_primaryKey()
        update_table_confirmation_querybox.queryLst = []
        update_table_confirmation_querybox.masterQueryLst = []
        self.fetchQueries()
        self.listWidget.itemClicked.connect(self.getQuery) # widget carrying all update queries for table with pri. key
        self.editQueries.clicked.connect(self.setup_GUI)
        self.no.clicked.connect(lambda:self.reject())
        self.yolo.clicked.connect(self.exeCUTE2_FINAL)
        self.execute_2.clicked.connect(self.exeCUTE2_TEST)
        self.insListWidget.itemDoubleClicked.connect(self.textPopup2) # widget carring all INSERt queries for table withOUT pri. key
        self.insListWidget.itemChanged.connect(self.update_masterQueryList)
        self.listWidget.itemChanged.connect(self.update_queryLst)
        self.execute.clicked.connect(self.exeCUTE1)
        self.execAll.toggled.connect(self.set_executeAll)
        self.exit.clicked.connect(lambda:self.reject())
        self.exit_2.clicked.connect(lambda:self.reject())
        self.desc.clicked.connect(self.descTable)
    
    def descTable(self):
        dlg = desc_table()
        if dlg.exec():
            return
    
    def setup_GUI(self):
        self.listWidget.itemDoubleClicked.connect(self.textPopup)
        self.listWidget.itemClicked.connect(self.getQuery)
        self.activeQuery.setText('Select a Query to Edit.')
        self.status.setText('')
    
    def textPopup2(self,item): # popup window allowing user to edit queries for exec method execute2()
        query = item.text()
    
        dlg = QInputDialog(self)                 
        dlg.setInputMode(QInputDialog.TextInput)
        dlg.setTextValue(query)
        dlg.setLabelText("Enter your Query:")
        dlg.setWindowIcon(QtGui.QIcon(QtGui.QPixmap('icon.png')))
        dlg.setWindowTitle('Edit Query')
        dlg.resize(500,100)                             
        ok = dlg.exec_()
        if ok:
            editedQuery = dlg.textValue()
            dlg = None
            if len(editedQuery) == 0:
                pass

            else:
                self.insListWidget.currentItem().setText(editedQuery)
                self.update_masterQueryList(self.insListWidget.currentItem())
  


    def textPopup(self,item): # popup window allowing user to edit queries for exec method execute1()
        
        self.activeQuery.setText('Select a Query.')
        self.status.setText('')
 
        query = item.text()
    
        dlg = QInputDialog(self)                 
        dlg.setInputMode(QInputDialog.TextInput)
        dlg.setTextValue(query)
        dlg.setLabelText("Enter your Query:")
        dlg.setWindowIcon(QtGui.QIcon(QtGui.QPixmap('icon.png')))
        dlg.setWindowTitle('Edit Query')
        dlg.resize(500,100)                             
        ok = dlg.exec_()
        if ok:
            editedQuery = dlg.textValue()
            dlg = None
            if len(editedQuery) == 0:
                row = self.listWidget.row(item)
                update_table_confirmation_querybox.queryLst.remove(query)
                self.activeQuery.setText('Select a Query.')
                self.listWidget.takeItem(row)
                self.listWidget.setCurrentRow(-1)
                
            else:
                self.listWidget.currentItem().setText(editedQuery)
                self.update_queryLst(self.listWidget.currentItem())
                update_table_confirmation_querybox.ACTIVE_QUERY = editedQuery
                self.activeQuery.setText('Select a Query.')
        
    def set_executeAll(self): # control GUI elements and determine whether to execute all queries; for exec method EXECUTE1()
        if self.execAll.isChecked():
            update_table_confirmation_querybox.exec_all = True
            self.listWidget.setEnabled(False)
            self.activeQuery.setText('Selected: ALL')

        else:
            update_table_confirmation_querybox.exec_all = False
            self.listWidget.setEnabled(True)
            self.activeQuery.setText('')
    
    def update_queryLst(self,item):   # function that updates the queryList with the newly changed query; for exec method EXECUTE1()
        queryLst = update_table_confirmation_querybox.queryLst
        row = self.listWidget.row(item)
        query = item.text()
        for i in range(len(queryLst)):
            if i == row:
                queryLst[i] = query
                break
        update_table_confirmation_querybox.queryLst = queryLst
    
    
    def update_masterQueryList(self,item): # function that updates the masterQueryList with the newly changed query; for exec method EXECUTE2()
        masterQueryList = update_table_confirmation_querybox.masterQueryList
        row = self.insListWidget.row(item)
        query = item.text()
        for i in range(len(masterQueryList)):
            if i == row:
                masterQueryList[i] = query
                break
        update_table_confirmation_querybox.masterQueryList = masterQueryList



    def getQuery(self,item):
        self.status.setText('Selected Query.')
        query = item.text()
        print('GETQUERY() Got QUERY:',query)
        update_table_confirmation_querybox.active_query_row = self.listWidget.row(item)
        update_table_confirmation_querybox.ACTIVE_QUERY = query
        self.activeQuery.setText("Selected: {}".format(query))

    
    def exeCUTE1(self):  # function to execute updation of table(s) WITH PRIMARY KEY
        global updated_DATA, update_table_query_lst
        queryLst = update_table_confirmation_querybox.queryLst
        if update_table_confirmation_querybox.exec_all == False:
            if self.listWidget.currentRow() == -1:
                popup = QMessageBox.about(self,'Select a Query','Please Select a Query to update.')
                return
            QUERY = update_table_confirmation_querybox.ACTIVE_QUERY
            try:
                mycur.execute(QUERY)
                myconn.commit()
                aqr = update_table_confirmation_querybox.active_query_row
                self.listWidget.takeItem(aqr)
                self.status.setText('Last selected query executed successfully.')
                self.listWidget.setCurrentRow(-1) 
                queryLst.remove(QUERY)
                                                
                self.activeQuery.setText('')
                update_table_confirmation_querybox.queryLst = queryLst
                update_table_query_lst = queryLst                     
                
                if self.listWidget.count() == 0 and update_table_query_lst == []:
                    update_table_confirmation_querybox.queryLst = []
                    updated_DATA = True
                    popup = QMessageBox.about(self,"Table updated successfully",'''\
All update queries have been executed.\nIn case you want to revert back from the update, you can get insert_data queries saved as a .txt file in the current \
working directory:\n{}\nN.B! Updating the table again will overwrite the file with newer queries.'''.format(str(os.getcwd())))
                    update_table_query_lst=[] # reset global var
                    self.backup_OriginalQueries()
                    self.accept()
                    
                    return
                else:
                
                    return
                
            except Exception as E:
                popup = QMessageBox.about(self,"UPDATE FAILED","UPDATE_DATA() EXECUTE1() FAILED!: {}".format(str(E)))
                self.backup_UPDATEDQueries()
                self.backup_OriginalQueries()
                popup = QMessageBox.about(self,"Queries have been backed up",'''\
The generated queries have been backed up as a .txt file, because of a failed update.\n\
You can find it in the current Working directory: \n{}\nYou can also find insert_data queries with the original data, in another .txt file.
                                                                           '''.format(str(os.getcwd())))
        
        else: # if needed to execute all queries
            print("EXECUTE1(ALL) QUERYLST:",queryLst)
            i = 1
            try:
                for eachQuery in queryLst:
                    mycur.execute(eachQuery)
                    myconn.commit()
                    i += 1
                update_table_confirmation_querybox.queryLst = []
    
                updated_DATA = True
                self.backup_OriginalQueries()
                popup = QMessageBox.about(self,"Table updated successfully",'''
All update queries have been executed.\nIn case you want to revert back from the update, you can get insert_data queries saved as a .txt file in the current \
working directory:\n{}\n'''.format(str(os.getcwd())))
                update_table_query_lst=[] #reset global var
                self.accept()

                
            except Exception as E:
                popup = QMessageBox.about(self,"UPDATE FAILED","UPDATE_DATA() EXECUTE1() FAILED!: {}".format(str(E)))
                self.backup_UPDATEDQueries()
                self.backup_OriginalQueries()
                popup = QMessageBox.about(self,"Queries have been backed up",'''\
The generated update queries have been backed up as a .txt file, because of a failed update.\
You can find it in the current Working directory: \n{}\nYou can also find insert_data queries with the original data, in another .txt file.
                                                                           '''.format(str(os.getcwd())))

    def exeCUTE2_TEST(self):
        MASTER_QUERY_LIST = update_table_confirmation_querybox.masterQueryList
        print("UPDATE_DATA() EXECUTE2(): TESTING QUERY().......")
        print("MASTER_QUERY_LIST:",MASTER_QUERY_LIST)
        i = 0
        try:
            
            for QUERY in MASTER_QUERY_LIST:
                mycur.execute(QUERY)
               
                i += 1
           
            print("UPDATE_DATA() EXECUTE2(): QUERY() PASS\nEXECUTED {} QUERIES.".format(i))
            self.exeCUTE2_FINAL()
            
        except Exception as E:
            self.stackedWidget.setCurrentIndex(self.stackedWidget.currentIndex() + 1)
            self.error.setText('Error: {}'.format(str(E)))
            self.errorType.setText('ErrorType: {}'.format(str(type(E))))
            self.backup_OriginalQueries()
            self.backup_UPDATEDQueries()
            msg = 'TXT File Backups of both UPDATED insert_data queries and ORIGINAL insert_data queries have been made in the current working directory:'
            self.cwd.setText(msg + '\n' + str(os.getcwd()))
            print("=================\nUPDATE_DATA() EXECUTE2_TEST() FAILED!\n===============")
            print('ErrorType: {}'.format(str(type(E))))
            print('Error: {}\nExecuted {} queries.'.format(str(E),i))

            
    def exeCUTE2_FINAL(self):
        global updated_DATA
        MASTER_QUERY_LIST = update_table_confirmation_querybox.masterQueryList
        print("UPDATE_DATA() EXECUTE2(): TESTING QUERY().......")
        print("MASTER_QUERY_LIST:",MASTER_QUERY_LIST)
        i = 0
        truncateQuery = "truncate table {}".format(DB_TB_choice[1])
        mycur.execute(truncateQuery)
        myconn.commit()
        try:
            
            for QUERY in MASTER_QUERY_LIST:
                mycur.execute(QUERY)
                
                i += 1
            myconn.commit()
            print("UPDATE_DATA() EXECUTE2(): ALL QUERIES() EXECUTED.\nEXECUTED {} QUERIES.".format(i))
            popup = QMessageBox.about(self,'Update Success', '''Table Data updated successfully.
\nIn case you want to revert back from the update, you can get insert_data queries saved as a .txt file in the current \
working directory:\n{}\nN.B! Updating the table again will overwrite the file with newer queries.'''.format(str(os.getcwd())))
            self.backup_OriginalQueries()
            updated_DATA = True
            self.accept()
            
            
        except Exception as E:
            msg = str(E)
            Type = str(type(E))
            popup = QMessageBox.about(self,'Update Failed', '''Table Data update failed.\nAll previous data had been lost.\
Please utilize the query backups saved in the current working directory, to retrieve lost data.\nErrorType: {}\nError:{}'''.format(msg,Type))
            
            self.backup_UPDATEDQueries()
            self.backup_OriginalQueries()
                
            print('UPDATE_DATA() EXECUTE2_FINAL() FAILED!')
            print('ErrorType: {}\nError: {}\Executed {} queries.'.format(Type,msg,i))
            print('TABLE TRUNCATED!!!')
            self.reject()
            
                                 
        
        
    
    
    


    
    def backup_OriginalQueries(self):
        original_queries = update_DATA.original_MASTER_QUERY  
        File=open('Update_DATA_{}_original_queries.txt'.format(str(DB_TB_choice)), 'w')
        File.write(original_queries)
        File.write("\n\nN.B!! If you are going to execute this on the MySQL-Frontend, execute each query ONE BY ONE on the Insert-Data page.")
        File.close()

    def backup_UPDATEDQueries(self):
        master_queries = update_DATA.MASTER_QUERY
        File=open('Update_DATA_{}_UPDATED_queries.txt'.format(str(DB_TB_choice)), 'w')
        File.write(master_queries)
        File.write("\n\nN.B!! If you are going to execute this on the MySQL-Frontend, execute each query ONE BY ONE on the Insert-Data page.")
        File.close()
 

	



    def fetchQueries(self): # fetch queries for listwidget for execute1()
        global update_table_query_lst
	

        if update_table_confirmation_querybox.queryLst == []:
            update_table_confirmation_querybox.queryLst = update_table_query_lst
        
        querylist=update_table_confirmation_querybox.queryLst #using active queryList from the popup's class
        
        for query in querylist:
            self.listWidget.addItem(query)
            query+='\n'
		
    def fetchInsQueries(self): # fetch queries for listwidget for execute2()
        masterQueryList = update_table_confirmation_querybox.masterQueryList
        for query in masterQueryList:
            self.insListWidget.addItem(query)
		
               
            
     
    def chk_for_primaryKey(self):
        global DB_TB_choice, myconn, mycur

        try:   # searches for primary key in the tablE
            query="desc {}".format(DB_TB_choice[1])
            mycur.execute(query)
            rs=mycur.fetchall()
            for row in rs:
                if row[3] == 'PRI':
                    self.stackedWidget.setCurrentIndex(0)
                    return True
                
            else:               
                self.stackedWidget.setCurrentIndex(1)
                
                update_table_confirmation_querybox.masterQuery = update_DATA.MASTER_QUERY
                update_table_confirmation_querybox.masterQueryList = update_DATA.MASTER_QUERY_LIST
				
                if update_table_confirmation_querybox.masterQuery == None or update_table_confirmation_querybox.masterQueryList == []:
                    print('Error:')
                    print('update_table_confirmation_querybox.masterQuery:',update_table_confirmation_querybox.masterQuery)
                    print('update_table_confirmation_querybox.masterQueryList:',update_table_confirmation_querybox.masterQueryList)
                    raise Exception("UPDATE_DATA() FATAL ERROR: INIT FAILED! [Update_tb_Popupdialog:chkForPrimaryKey()]: MasterQuery and/or MasterQueryList are empty!")
                    self.reject() 
                else:
                    self.fetchInsQueries()
                    return False
            
                    
            

        except Exception as E:
            msg="ERROR: {}".format(str(E)) + "\nType: {}".format(str(type(E)))
            print(msg)
            popup=QMessageBox.about(self,'ERROR - Check for PRI FAIL',msg)




#========  /----   /-----    -----   -----  -----  /\        /   /----   ==============================
#=======  /       /         /   /   /      /      /  \      /   /       ===============================
#======  /----/  /         /\---   -----  -----  /    \    /   /----/  ================================
#=====       /  |         /  \    /      /      /      \  /        /  =================================
#====   ----/    \----   /    \  -----  -----  /        \/    ----/  ==================================

class wel_Login_scr(QDialog):
    def __init__(self):
        super(wel_Login_scr, self).__init__()
        loadUi('login_02.ui', self)
        
        self.loginbtn.clicked.connect(self.loginfunction)
        self.helpbtn.clicked.connect(self.helpPopup)
    
    def gotoDBScr(self):
        DB_scr = get_DB_scr()
        widget.addWidget(DB_scr)
        widget.setCurrentIndex(widget.currentIndex()+1)
        print(widget.currentIndex())
    
    
    def helpPopup(self):
        print('User Clicked loginHelp Btn.')
        msg="""
This program is designed to work on MySQL Server v5.1.33 and above, installed \
NATIVELY on your computer.

Default Username: root
Default Password: <password that was used to set up MySQL Installation>
            """
        popup=QMessageBox.about(self,'Help',msg)
        
    
        
    def loginfunction(self):
        User = self.usrbox.text()
        password = self.pwdbox.text()
        login_status=False
        if len(User)==0 or len(password)==0:
            self.Error.setText("Error: Please input all fields.")
            print("\aError: User didn't enter required details.")
        else:
            try:
                global myconn
                global mycur

                global usr_data
                myconn=sql.connect(host='localhost', user=User, passwd=password)
                mycur=myconn.cursor(buffered = True)
                login_status=True
                print('Login Success!','Username:',User)
                usr_data.append(User)
                usr_data.append(password)
                self.Error.setText("")
            except Exception as E:
                print('Login Error:',E)
                self.Error.setText('Login failed! Error: ' + str(E))
                print('\a')
                login_status=False
        if login_status==True:
            self.gotoDBScr()
        else:
            pass
            

            



class get_DB_scr(QDialog):
    global DB_TB_choice, widget
    def __init__(self):
        super(get_DB_scr,self).__init__()
        loadUi("pick db.ui",self)
        self.Logoutbtn.clicked.connect(self.logout)
        self.Proceedbtn.clicked.connect(self.Proceed_chk)
        self.tabWidget.setEnabled(False)
        self.Error.setText('')
        self.FetchDB()
        self.modify_DB.toggled.connect(self.enable_mod_DB)
        self.listWidget.itemClicked.connect(self.select_DB)
        self.delete_DB.clicked.connect(self.delete_db)
        self.rename_DB.clicked.connect(self.rename_db)      #DOES WORK, OLD DB GETS DELETED. VERY DELICATE FUNCTION.
        self.insert_DB.clicked.connect(self.insert_database)
        
    
    def insert_database(self):
        self.Error.setText("")
        new_DB = self.new_DB_txtbox.text()
        if new_DB == '':
            self.Error.setText("ERROR: A DB with an empty name cannot be inserted.")
            print('\a')
        else:
            self.Error.setText("")
            global myconn, mycur
            try:
                query="create database {}".format(new_DB)
                mycur.execute(query)
                myconn.commit()
                time.sleep(2)
                print('\a')
                self.FetchDB()
                self.insert_DB.setEnabled(True)
                self.selection.setText("")
                popup=QMessageBox.about(self,'Success',"DB inserted.")
            except Exception as E:
                self.Error.setText("Error: " +str(E))
                self.selection.setText("")
                self.FetchDB()
                print('\a')
        
    def delete_db(self):
        if len(DB_TB_choice) == 0:
            msg="No Database was selected."
            popup=QMessageBox.about(self,'COULDN\'T DELETE',msg)
        else:
            dlg = delete_db_confirmation(self)
            if dlg.exec():
                if DB_TB_choice[0] == None:
                    self.delete_selection_label.setText('')
                    self.rename_selection_label.setText("")
                    self.selection.setText("")
                self.FetchDB()
                exit
    
    def enable_mod_DB(self):
        if self.modify_DB.isChecked():
            self.tabWidget.setEnabled(True)
        else:
            self.tabWidget.setEnabled(False)
        
               
    def select_DB(self):
        global DB_TB_choice
        DB_TB_choice=[]
        ITEM=self.listWidget.currentItem()
        DB=ITEM.text()
        DB_TB_choice.append(DB)
        selection_="Selected DB: {}".format(DB)
        self.rename_selection_label.setText(selection_)
        self.delete_selection_label.setText(selection_)
        self.selection.setText(selection_)
        
        
    
 
    def logout(self):
        global login_status
        login_status = False
        print('User logged out.')
        self.gotologinpg()
    
    def gotologinpg(self):
        loginpg = wel_Login_scr()
        widget.addWidget(loginpg)
        widget.setCurrentIndex(widget.currentIndex()+1)
        print(widget.currentIndex())
     
    def FetchDB(self):
        global myconn, mycur, DB_list
        self.listWidget.clear()
        query = 'show databases'
        mycur.execute(query)
        rs=mycur.fetchall()
        for row in rs:
            DB_list.append(row[0])
            self.listWidget.addItem(row[0])
            
    def Proceed_chk(self):
        if len(DB_TB_choice) == 0:
            self.Error.setText('Error: Select a DB to proceed.')
        else:
            #DB_TB_choice.append(str(ITEM.text())) #appends DB
            DB_TB_choice.append(None)   #appends NoneType to be replaced with TB
            self.Error.setText('')
            self.gotomainpg()
    def rename_db(self):   # ;)
        global DB_TB_choice, renamed_DB
        renamed_DB=self.rename_txtbox.text()
        if len(DB_TB_choice) == 0:
            self.Error.setText('Error: Select a DB to proceed.')
            print('\a')
            self.main_label.setText("Pick your Database:")           
        elif len(renamed_DB)==0:
            popup=QMessageBox.about(self,'Error','DB cannot be renamed to an empty string.')
        else:
            self.Error.setText('')
            self.selection.setText("")
            #renamed_DB=self.rename_txtbox.text()
            popup=rename_db_confirmation(self)
            if popup.exec():
                if DB_TB_choice[0] == None:
                    self.rename_selection_label.setText('Selected DB:<none>')
                self.rename_txtbox.clear()
                renamed_DB=None
                print('left DB rename function')
                self.main_label.setText("Pick your Database:")
                self.FetchDB()
    
    def gotomainpg(self):
        global usr_data, myconn, mycur, DB_TB_choice
        print('User selected DB:',DB_TB_choice[0])
        time.sleep(1.5)
        myconn=None
        mycur=None
        User=usr_data[0]
        Password=usr_data[1]
        DB=DB_TB_choice[0]
        myconn=sql.connect(host='localhost', user=str(User), passwd=Password, database=DB) #resets myconn and mycur
        mycur=myconn.cursor()
        main_window=MainWindow()
        widget.addWidget(main_window)
        widget.setCurrentIndex(widget.currentIndex()+1)
        print(widget.currentIndex())
        

class MainWindow(QDialog):
    def __init__(self):
        global DB_TB_choice
        super(MainWindow, self).__init__()
        loadUi('main-window.ui',self)
        self.Error.setText("")
        self.go_back_btn.clicked.connect(self.goback)
        self.DB_label.setText(DB_TB_choice[0])
        if DB_TB_choice[1] == None:
            self.TB_label.setText("<none>")
            self.alt_TB_label.setText("<none>")
        else:
            self.TB_label.setText(str(DB_TB_choice[1]))
            self.alt_TB_label.setText(str(DB_TB_choice[1]))
        self.getTB()
        self.Insert_btn.clicked.connect(self.gotoInsertDATA)
        self.add_col.clicked.connect(self.goto_add_col)
        self.TBlistwidget.itemClicked.connect(self.selectTB)
        self.new_tb.clicked.connect(self.goto_newTB)
        self.Display_btn.clicked.connect(self.displayAllDATA)
        self.delete_TB.clicked.connect(self.delete_tb)
        self.rename_TB.clicked.connect(self.rename_tb)
        self.logout_btn.clicked.connect(self.gotologinpg)
        self.delete_col.clicked.connect(self.deleteColumn)
        self.descTB.clicked.connect(self.describeTB)
        self.modify_col.clicked.connect(self.gotoModifyCol)
        self.rename_col.clicked.connect(self.renameCol)
        self.Delete_btn.clicked.connect(self.Delete_Data)
        self.Update_btn.clicked.connect(self.Update_Data)
        self.selectiveDisplay_btn.clicked.connect(self.goto_selectiveDisplay)
        self.resetMyConn.clicked.connect(self.resetMySQLConn)
    
    def resetMySQLConn(self):
        global myconn, mycur
        try:
            myconn = sql.connect(host='localhost', user=usr_data[0], password=usr_data[1], database = DB_TB_choice[0])
            mycur = myconn.cursor(buffered = True)
            if myconn.is_connected():
                msg = "Connection to MySQL Server has been reset."
                popup = QMessageBox.about(self,"Connection Reset",msg)
                return
        except Exception as E:
            msg = "Connection Reset Failed: {}".format(str(E))
            popup = QMessageBox.about(self,"Connection Reset Failed", msg)
    
    
    
    
    
    def renameCol(self):
        global DB_TB_choice, myconn, mycur
        if DB_TB_choice[1] == None:
            self.Error.setText("ERROR: Select a Table to proceed")
            print('\a')
        
        else:
            self.Error.setText('')
            try:
                query="desc {}".format(DB_TB_choice[1])
                mycur.execute(query)
                rs=mycur.fetchall()
                if rs == []:
                    msg = "This table '{}' has no saved attributes to modify.".format(DB_TB_choice[1])
                    popup = QMessageBox.about(self,"ERROR",msg)
                else:
                    rename_COL=rename_Col_confirmation()
                    if rename_COL.exec():
                        print('\aLeft rename column function.')
            except Exception as E:
                msg = "ERROR: " + str(E)
                popup = QMessageBox.about(self,"ERROR",msg)
                print('\a') 
    
    
        
    def gotoModifyCol(self):
        global DB_TB_choice, myconn, mycur
        if DB_TB_choice[1] == None:
            self.Error.setText("ERROR: Select a Table to proceed")
            print('\a')
        
        else:
            self.Error.setText('')
            try:
                query="desc {}".format(DB_TB_choice[1])
                mycur.execute(query)
                rs=mycur.fetchall()
                if rs == []:
                    msg = "This table '{}' has no saved attributes to modify.".format(DB_TB_choice[1])
                    popup = QMessageBox.about(self,"ERROR",msg)
                else:
                    mod_COL=modify_tb_column()
                    widget.addWidget(mod_COL)
                    widget.setCurrentIndex(widget.currentIndex()+1)
                    print(widget.currentIndex())
            except Exception as E:
                msg = "ERROR: " + str(E)
                popup = QMessageBox.about(self,"ERROR",msg)
                print('\a') 
    
    def describeTB(self):
        global DB_TB_choice, myconn, mycur
        if DB_TB_choice[1] == None:
            self.Error.setText("ERROR: Select a Table to proceed")
            print('\a')
        
        else:
            self.Error.setText('')
            try:
                query="desc {}".format(DB_TB_choice[1])
                mycur.execute(query)
                rs=mycur.fetchall()
                if rs == []:
                    msg = "This table '{}' has no saved attributes to describe.".format(DB_TB_choice[1])
                    popup = QMessageBox.about(self,"ERROR",msg)
                else:
                    dlg = desc_table(self)
                    if dlg.exec():
                        pass
            except Exception as E:
                msg = "ERROR: " + str(E)
                popup = QMessageBox.about(self,"ERROR",msg)
                print('\a') 
    
    
    def deleteColumn(self):
        
        global DB_TB_choice, myconn, mycur
        if DB_TB_choice[1] == None:
            self.Error.setText("ERROR: Select a Table to proceed")
            print('\a')
        
        else:
            self.Error.setText('')
            try:
                query="desc {}".format(DB_TB_choice[1])
                mycur.execute(query)
                rs=mycur.fetchall()
                if rs == []:
                    msg = "This table '{}' has no saved attributes to delete.".format(DB_TB_choice[1])
                    popup = QMessageBox.about(self,"ERROR",msg)
                else:
                    dlg=delete_Column_confirmation(self)
                    if dlg.exec():
                        pass
            except Exception as E:
                msg = "ERROR: " + str(E)
                popup = QMessageBox.about(self,"ERROR",msg)
                print('\a') 
        
            
               # print("A TB just got deleted.")
                #self.TB_label.setText("<none #self.alt_TB_label.setText("<none>")
               # self.getTB()
        
    def delete_tb(self):
        global DB_TB_choice
        if DB_TB_choice[1] == None:
            self.Error.setText("ERROR: Select a Table.")
            print('\a')
        else:
            self.Error.setText('')
            dlg=delete_tb_confirmation(self)
            if dlg.exec():
                print("LEFT delete table function")
                self.TB_label.setText("<none>")
                self.alt_TB_label.setText("<none>")
                self.getTB()
    
    def rename_tb(self):
        global DB_TB_choice
        if DB_TB_choice[1] == None:
            self.Error.setText("ERROR: Select a Table.")
            print('\a')
        else:
            self.Error.setText('')
            dlg=rename_tb_confirmation(self)
            if dlg.exec():
                print("Left Rename table function")
                self.TB_label.setText("<none>")
                self.alt_TB_label.setText("<none>")
                self.getTB()
    
    def displayAllDATA(self):
        global DB_TB_choice, myconn, mycur
        if DB_TB_choice[1] == None:
            self.Error.setText("ERROR: Select a Table to proceed.")
            print('\a')
        
        else:
            self.Error.setText('')
            try:
                query="select * from {}".format(DB_TB_choice[1])
                mycur.execute(query)
                rs=mycur.fetchall()
                if rs == []:
                    msg = "This table '{}' has no data to be displayed.".format(DB_TB_choice[1])
                    popup = QMessageBox.about(self,"ERROR",msg)
                else:
                    TBwin = display_table(self)
                    if TBwin.exec():
                        exit
            except Exception as E:
                msg = "ERROR: " + str(E)
                popup = QMessageBox.about(self,"ERROR",msg)
                print('\a') 

    

    
    def Delete_Data(self):
        global DB_TB_choice, myconn, mycur
        if DB_TB_choice[1] == None:
            self.Error.setText("ERROR: Select a Table to proceed.")
            print('\a')
        
        else:
            self.Error.setText('')
            try:
                query="select * from {}".format(DB_TB_choice[1])
                mycur.execute(query)
                rs=mycur.fetchall()
                if rs == []:
                    msg = "This table '{}' has no data saved.".format(DB_TB_choice[1])
                    popup = QMessageBox.about(self,"ERROR",msg)
                else:
                    del_DAT_win = delete_data_confirmation(self)
                    if del_DAT_win.exec():
                        print('\a')
                        exit
            except Exception as E:
                msg = "ERROR: " + str(E)
                popup = QMessageBox.about(self,"ERROR",msg)
                print('\a') 
            
    def goto_selectiveDisplay(self):
        global DB_TB_choice, myconn, mycur
        if DB_TB_choice[1] == None:
            self.Error.setText("ERROR: Select a Table to proceed.")
            print('\a')
        
        else:
            self.Error.setText('')
            try:
                query="select * from {}".format(DB_TB_choice[1])
                mycur.execute(query)
                rs=mycur.fetchall()
                if rs == []:
                    msg = "This table '{}' has no data to be displayed.".format(DB_TB_choice[1])
                    popup = QMessageBox.about(self,"ERROR",msg)
                else:
                    TBwin = selectiveDisplay_table(self)
                    if TBwin.exec():
                        exit
            except Exception as E:
                msg = "ERROR: " + str(E)
                popup = QMessageBox.about(self,"ERROR",msg)
                print('\a') 
    
    
    def gotoInsertDATA(self):
        global DB_TB_choice
        if DB_TB_choice[1] != None:
            self.Error.setText("")
            insert=insert_Data()
            widget.addWidget(insert)
            widget.setCurrentIndex(widget.currentIndex()+1)
            print(widget.currentIndex())
        else:
            self.Error.setText("ERROR: Select a Table to proceed.")
            print('\a')
    
    def goto_add_col(self):
        global DB_TB_choice
        ITEM = self.TBlistwidget.currentItem()
        if ITEM==None:
            self.Error.setText('ERROR: Select a Table.')
            print('\aERROR: Select a Table.')
        else:
            TB=ITEM.text()
            self.Error.setText('')
            addTBcol=Add_tb_column()
            widget.addWidget(addTBcol)
            widget.setCurrentIndex(widget.currentIndex()+1)
            print(widget.currentIndex())
          
    def goto_newTB(self):
        addTB=Add_tb()
        widget.addWidget(addTB)
        widget.setCurrentIndex(widget.currentIndex()+1)
        print(widget.currentIndex())
        
    def selectTB(self):
        self.Error.setText('')
        global DB_TB_choice
        ITEM=self.TBlistwidget.currentItem()
        TB=ITEM.text()
        DB_TB_choice[1]=TB
        self.TB_label.setText(TB)
        self.alt_TB_label.setText(TB)
      
        
    def logout(self):
        global login_status, DB_TB_choice
        login_status = False
        print('User logged out.')
        self.gotologinpg()
        DB_TB_choice=[]
    def gotologinpg(self):
        global login_status
        login_status=False
        loginpg = wel_Login_scr()
        widget.addWidget(loginpg)
        widget.setCurrentIndex(widget.currentIndex()+1)
        print(widget.currentIndex())
    def goback(self):
        global DB_TB_choice
        DB_TB_choice=[]
        db_menu = get_DB_scr()
        widget.addWidget(db_menu)
        widget.setCurrentIndex(widget.currentIndex()+1)
        print(widget.currentIndex())
        
        
    def getTB(self):
        self.TBlistwidget.clear()
        global mycur, TB_list
        try:
            query2 = 'show tables'
            mycur.execute(query2)
            rs=mycur.fetchall()
            for row in rs:
                TB_list.append(row[0])
                self.TBlistwidget.addItem(row[0])
        except Exception as E:
            msg="ERROR: " + str(E)
            popup=QMessageBox.about(self,"INTERNAL ERROR",msg)
            print("\aERROR: " + str(E))
    
    def Update_Data(self):
        global DB_TB_choice, myconn, mycur, widget
        if DB_TB_choice[1] == None:
            self.Error.setText("ERROR: Select a Table to proceed.")
            print('\a')
        
        else:
            self.Error.setText('')
            try: 
                query="select * from {}".format(DB_TB_choice[1])
                mycur.execute(query)
                rs=mycur.fetchall()
                if rs == []:
                    msg = "This table '{}' has no data to be updated.".format(DB_TB_choice[1])
                    popup = QMessageBox.about(self,"ERROR",msg)
                else:
                    TBwin = update_DATA()
                    widget.addWidget(TBwin)
                    widget.setCurrentIndex(widget.currentIndex()+1)
                    print(widget.currentIndex())
            except Exception as E:
                msg='ERROR: {}'.format(str(E))
                popup=QMessageBox.about(self,'ERROR',msg)
    
    

class update_DATA(QDialog):
    # enclosed class var
    
    # QUERYGEN1() ---> generates the query for tables WITH PRIMARY KEY
    # QUERYGEN2() ---> generates the query for tables WITHOUT PRIMARY KEY
    
    case_sensitive=None         # None -> [Bool] for case sensitive search() for data
    original_MASTER_QUERY=''    # backup masterQuery [str with all queries] of the unmodified table generated by QUERYGEN2()
    MASTER_QUERY=""             # [str with all queries] masterQuery of the MODIFIED table generated by
                                #              QUERYGEN2() if table has no primary key
                                #              QUERYGEN1() if table has primary key
                                
    primary_key_exists=None     #[IMPORTANT]  None -> [bool] to check if primary key is present in table 
    table_DATA=[]
    columns=[]                  #[list] column_names of table fetched by fetch_DATA()
    MASTER_QUERY_LIST = []		#[list with queries saved seperately] insert_into_table_data queries fetched by QueryGEN2()
    def __init__(self):
        super(update_DATA,self).__init__()
        loadUi("update_TB.ui",self)
        self.caseSensitive.toggled.connect(self.search_caseSensitivity)
        self.tableWidget.itemChanged.connect(self.queryGEN1)
        self.fetchColumns()
        self.go_back.clicked.connect(self.goBack)
        self.exit.clicked.connect(self.goBack)
        self.selectedTB.setText("Selected Table: {}".format(DB_TB_choice[1]))
        self.fetch_DATA()
        self.search.clicked.connect(self.searchFor_DATA)
        self.updator.clicked.connect(self.update)
        self.reload.clicked.connect(self.Reload) #reload the page
        self.display_all_DATA.clicked.connect(self.displayAll_DATA)
        self.col_listWidget.itemClicked.connect(lambda:self.selected_Col.setText("Selected Attribute: {}".format(self.col_listWidget.currentItem().text())))
        update_DATA.primary_key_exists = self.chk_for_primaryKey()
        update_DATA.original_MASTER_QUERY = self.queryGEN2()[0] # queryGEN2() returns (masterQuery[str],masterQueryList[list])
    
    def search_caseSensitivity(self):
        if self.caseSensitive.isChecked():
            update_DATA.case_sensitive = True
        else:
            update_DATA.case_sensitive = False
    
    def Reload(self):
        self.tableWidget.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked)
        self.updator.setEnabled(False)
        self.headerLabel.setText('Double-Click and update the data on the Table.')
        self.infoLabel.setText('')


    #__main function__
    def queryGEN1(self,item):    # generates query for table(s) WITH PRIMARY KEY
        global update_table_query_lst
       
        # setup GUI
        if item == self.tableWidget.currentItem():
            if item.row() == 0 or item.column() == 0:
                self.Reload()
                self.reload.setEnabled(False)

                return

            self.updator.setEnabled(True)
            global update_query_lst
            self.infoLabel.setText('Update has been saved.')
            
            # begin QUERYGEN1()
            if update_DATA.primary_key_exists:
                PRI_Key=None #actual primary key
                try:
                    query='describe {}'.format(DB_TB_choice[1]) # searches for primary key in the table
                    mycur=myconn.cursor(buffered=True)
                    mycur.execute(query)
                    myconn.commit()
                    rs=mycur.fetchall()
                    for row in rs:
                        if row[0] in update_DATA.columns:
                            PRI_Key=row[0] #======obtained primary key=========
                            break # only one primary key in a table

                except Exception as E:
                    msg="ERROR: - Check for PRI FAIL setup_TBwidget(1):{}".format(str(E)) + "\nType: {}".format(str(type(E)))
                    print(msg)
                    popup=QMessageBox.about(self,'ERROR - Check for PRI FAIL',msg)
                    return
            
                pri_col_index=None
                columns=update_DATA.columns
                print('Columns:',columns)
                print('PRI:',PRI_Key)
                for column in columns:
                    if column == PRI_Key:
                        pri_col_index = columns.index(column) # getting column index without slno
                        print('pri_col_index:',pri_col_index)
                        break
            
                row_count=self.tableWidget.rowCount() #absolute rowCount WYSIWYG on tableWidget
                column_count=self.tableWidget.columnCount() #absolute columnCount 
                
                #edited item
                item = self.tableWidget.currentItem()
                abs_item_row_index = item.row() - 1
                abs_item_col_index = item.column() - 1
                item_col_name = update_DATA.columns[abs_item_col_index]
                item_DATA = item.text()
                if item_DATA == 'None' or item_DATA == 'NULL':  # fixed None <--> NULL bug
                    item_DATA = 'NULL'
               
                

                corr_PRI_DATA = self.tableWidget.item(abs_item_row_index + 1,pri_col_index + 1).text() #getting corresponding pri_key item for update ref 
               
                    # the edited item has common ROW_INDEX as the primary_key reference item but the reference item will hv COL_INDEX
                        # as defined by "PRI_COL_INDEX + 1" ACCOUNTING FOR THE sl_no
                    
                    
             
                    
                corr_PRI_DATA = update_DATA.table_DATA[abs_item_row_index][pri_col_index]
                print('primary key:',PRI_Key)
                print('old pri_key data:',corr_PRI_DATA)
                print('col_name_TBU:',item_col_name)  #col_name_TBU --> column name To Be Updated
                print('NEW_col_DATA:',item_DATA)
                    
                    # var item_DATA datatype deciphering..........
                try:    # found no other way for float()
                    float(item_DATA)
                    Query="update {} set {}={} where".format(DB_TB_choice[1], item_col_name, item_DATA)
                            
                except Exception:
                    if item_DATA == 'NULL':
                        Query="update {} set {}={} where".format(DB_TB_choice[1], item_col_name, item_DATA)
                    else:
                        if item_DATA.isalnum(): # saves query with quotes for the corresponding primary key data
                            Query="update {} set {}=\"{}\" where".format(DB_TB_choice[1], item_col_name, item_DATA)
                        else:
                            Query="update {} set {}=\"{}\" where".format(DB_TB_choice[1], item_col_name, item_DATA)
                    
                    # var corr_PRI_DATA datatype deciphering.........
                try:
                    float(corr_PRI_DATA)
                    Query += " {}={};".format(PRI_Key,corr_PRI_DATA)
                except Exception:
                    if corr_PRI_DATA.isalnum(): #saves query with quotes for the corresponding primary key data
                        Query +=" {}=\"{}\";".format(PRI_Key,corr_PRI_DATA)
                    else:
                        Query +=" {}=\"{}\";".format(PRI_Key,corr_PRI_DATA)
                
                print("QUERYGEN1() SUCCESS!")
                print("QUERY:",Query)
                update_table_query_lst.append(Query)
                
                update_DATA.MASTER_QUERY += Query + '\n\n'
               
             

#---|---|---|
                      

    
    def chk_for_primaryKey(self):
        global DB_TB_choice, myconn, mycur

        try:   # searches for primary key in the tablE
            query="desc {}".format(DB_TB_choice[1])
            mycur.execute(query)
            rs=mycur.fetchall()
            for row in rs:
                if row[3] == 'PRI':
                    return True
                
            else:
                self.pri_key_warn.setText('No Primary Key found')
                return False
            
                    
            

        except Exception as E:
            msg="ERROR: {}".format(str(E)) + "\nType: {}".format(str(type(E)))
            print(msg)
            popup=QMessageBox.about(self,'ERROR - Check for PRI FAIL',msg)

    
    def displayAll_DATA(self):
        TBwin = display_table(self)
        if TBwin.exec():
            return
    
    def searchFor_DATA(self):
        item_TBS=self.data_lineEdit.text()
        item_TBS_row=[]
        item_TBS_col=[]
        case_sensitive = update_DATA.case_sensitive
        row_count=self.tableWidget.rowCount()
        column_count=self.tableWidget.columnCount()
        for r_i in range(1,row_count):
            for c_i in range(1, column_count):
                if case_sensitive == True:
                    if self.tableWidget.item(r_i,c_i).text() == item_TBS:
                        item_TBS_row.append(r_i + 1)
                        item_TBS_col.append(c_i + 1)
                else:
                    if self.tableWidget.item(r_i,c_i).text().upper() == item_TBS.upper():
                        item_TBS_row.append(r_i + 1)
                        item_TBS_col.append(c_i + 1)

        if item_TBS_row == [] and item_TBS_col == []:
            self.infoLabel.setText("Can\'t find the item '{}'.".format(item_TBS))
        elif len(item_TBS_row) == 1 and len(item_TBS_col) == 1:
            self.infoLabel.setText("Object is found at Row: '{}' and Column: '{}'.".format(item_TBS_row[0],item_TBS_col[0]))
            self.tableWidget.scrollToItem(self.tableWidget.item(item_TBS_row[0],item_TBS_col[0]),hint=QAbstractItemView.EnsureVisible)
            self.tableWidget.setCurrentCell(item_TBS_row[0]-1,item_TBS_col[0]-1)
        else:
            self.infoLabel.setText("Object is found at Rows: '{}' and Columns: '{}'.".format(str(item_TBS_row),str(item_TBS_col)))
        self.selected_Col.setText("")       
                
    def update(self):
        global updated_DATA, update_table_query_lst
        update_DATA.MASTER_QUERY = self.queryGEN2()[0] # queryGEN2() returns (masterQuery[str],masterQueryList[list])
        update_DATA.MASTER_QUERY_LIST = self.queryGEN2()[1] 
        update_TB_querybox=update_table_confirmation_querybox()
        if update_TB_querybox.exec():
            if updated_DATA == True or update_table_query_lst == []:
                self.stackedWidget.setCurrentIndex(self.stackedWidget.currentIndex() + 1)
                updated_DATA = False
                return
            elif update_table_query_lst != []:
                updated_DATA = False
                return

            else:
                goback=MainWindow()
                widget.addWidget(goback)
                widget.setCurrentIndex(widget.currentIndex()+1)
                print(widget.currentIndex())
                updated_DATA = False # resetting global var

    #__main_Function__
    def queryGEN2(self):  # generates query for table(s) WITHOUT PRIMARY KEY
        # begin QUERYGEN2()
        global DB_TB_choice, myconn, mycur
        columns = update_DATA.columns
        DATA = []
        MASTER_QUERY=''
        row_count=self.tableWidget.rowCount()
        col_count=self.tableWidget.columnCount()
        #getting data from table into rowDATA
        for row_index in range(row_count):
            rowDATA = []
            for col_index in range(col_count):
                if self.tableWidget.item(row_index,col_index).text().upper() == 'NONE':
                    rowDATA.append(None)
                else:
                    rowDATA.append(self.tableWidget.item(row_index,col_index).text())
            DATA.append(rowDATA)

        print('QUERYGEN2() DATA:',DATA)
        try:
            #generate column string
            column_str = "("
            for column in columns:
                column_str += str(column) + ' ,'
            column_str=column_str[:-2]
            column_str+=")"
            print("Column_STR:",column_str)
            print('QUERYGEN2() GENERATING QUERY.....')
            QueryList = []
            # generating row elements
            for i in range(1,row_count): #for every row iteration
                row = "("
                for k in range(1,len(list(DATA[i]))): #for every col ite
                    try:
                        float(DATA[i][k])
                        row += "{}, ".format(DATA[i][k])
                    except Exception:
                        if DATA[i][k] == None:
                            DATA[i][k] = 'NULL' #fixed None <--> NULL bug
                            row += "{}, ".format(DATA[i][k])
                        elif DATA[i][k].isdigit():
                            row += "{}, ".format(DATA[i][k])
                        else:
                            if DATA[i][k].isalnum():        # saves it as String
                                row += "\"{}\", ".format(DATA[i][k])
                            else:                       # saves it as string
                                row += "\"{}\", ".format(DATA[i][k])
                    
                row=row[:-2]
                row += ');\n\n'
                
                QUERY = "insert into {} {} values{}".format(DB_TB_choice[1],column_str,row)
                QueryList.append(QUERY)
            # generating MASTER_QUERY
            for QUERIE in QueryList:
                MASTER_QUERY += QUERIE
            print("QUERYGEN2() QUERY GENERATION SUCCESS!")
            MASTER_QUERY = MASTER_QUERY[:-2]
            MASTER_QUERY_LIST = MASTER_QUERY.split('\n\n')
            print("QUERY:",MASTER_QUERY)
            print("QUERY_LIST:",MASTER_QUERY_LIST)
            return MASTER_QUERY, MASTER_QUERY_LIST
        except Exception as E:
            print("QUERYGEN2() FAILED!, " + str(E))
            popup=QMessageBox(self, 'QUERYGEN2() FAILED!',"QUERYGEN2() FAILED!, " + str(E))
            return



    def fetch_DATA(self):
        global DB_TB_choice, myconn, mycur
        try:
            query2="select * from {}".format(DB_TB_choice[1])
            mycur.execute(query2)
            rs2=mycur.fetchall()
            update_DATA.table_DATA=rs2
            column_names=mycur.column_names
            update_DATA.columns=column_names
            if rs2 == []:
                msg="No data is saved in this table.\n"
                popup=QMessageBox.about(self,'Alert',msg)
                return
                    
            else:
                rowcount=mycur.rowcount
                for row in rs2:
                    columncount=len(row)
                self.tableWidget.setRowCount(rowcount+1)
                self.tableWidget.setColumnCount(columncount+1)
                self.tableWidget.setItem(0,0,QTableWidgetItem("Sl.No"))
                self.tableWidget.item(0,0).setBackground(QtGui.QColor(191,239,239))
                i=0
                for column_name in column_names:
                    i+=1
                    self.tableWidget.setItem(0,i,QTableWidgetItem(column_name))
                    self.tableWidget.item(0,i).setBackground(QtGui.QColor(191,239,239))
                for r_i in range(1, rowcount+1):
                    self.tableWidget.setItem(r_i,0,QTableWidgetItem(str(r_i)))
                    for c_i in range(1, columncount+1):
                        self.tableWidget.setItem(r_i,c_i,QTableWidgetItem(str(rs2[r_i - 1][c_i - 1])))
                
            
        except Exception as E:
            msg = "Error: {}".format(str(E)) + "\nType: {}".format(type(E))
            print(msg,'\a')
            popup=QMessageBox.about(self,'ERROR',msg)
    
    
    
    
    def goBack(self):
        goback=MainWindow()
        widget.addWidget(goback)
        widget.setCurrentIndex(widget.currentIndex()+1)
        print(widget.currentIndex())
    
    def fetchColumns(self):
        global DB_TB_choice, myconn, mycur
        try:
            query="desc {}".format(DB_TB_choice[1])
            mycur.execute(query)
            rs=mycur.fetchall()
            if rs == []:
                msg="No column found in this table."
                popup=QMessageBox.about(self,"Alert",msg)
                print('\a',msg)
            else:
                for row in rs:
                    self.col_listWidget.addItem(row[0])
                print('Fetched all Columns.')
        except Exception as E:
            Msg="Error: {}".format(str(E))
            popup=QMessageBox.about(self,"INITIALIZATION ERROR",Msg)
            print(msg,'\n\a')
        





class Add_tb_column(QDialog):
    def __init__(self):
        super(Add_tb_column,self).__init__()
        loadUi('add_TB_column.ui',self)
        self.aexecuTOR.clicked.connect(self.execute)
        self.anewline.clicked.connect(self.add_newLine)
        self.aQuerybox.textCursor().insertText("alter table {} add ".format(DB_TB_choice[1]))
        self.aback_btn.clicked.connect(self.goBack)
        self.aAttrib_appenDOR.clicked.connect(self.attrib_appendor)
        self.aendQuery.clicked.connect(self.endquery)
        self.ahelp.clicked.connect(self.helpPopup)
        self.ahelp_2.clicked.connect(self.helpPopup)
        self.aTBlistwidget.itemDoubleClicked.connect(self.selectTB)
        self.getTB()
        self.adescribe_TB.clicked.connect(self.describe_table)
        self.aTB_selector_label.setText("Selected:'{}'".format(DB_TB_choice[1]))
        self.aTB_label.setText("Selected Table:{}".format(DB_TB_choice[1]))
        self.primaryKey_checker()
    
    def describe_table(self):
        dlg = desc_table()
        if dlg.exec():
            return
    
    def primaryKey_checker(self):
        global DB_TB_choice, myconn, mycur
        try:
            query="desc {}".format(DB_TB_choice[1])
            mycur.execute(query)
            rs=mycur.fetchall()
            if rs == []:
                self.aprimarykey_checkBox.setEnabled(True)
            else:
                for row in rs:
                    if row[3].upper() == 'PRI':
                        self.aprimarykey_checkBox.setEnabled(False)
                        break
                else:
                    self.aprimarykey_checkBox.setEnabled(True)
        except Exception as E:
            msg="ERROR: " + str(E)
            popup=QMessageBox.about(self,"INTERNAL ERROR",msg)
            print("\aERROR: " + str(E))
    
    def goBack(self):
        goback=MainWindow()
        widget.addWidget(goback)
        widget.setCurrentIndex(widget.currentIndex()+1)
        print(widget.currentIndex())
    
    def execute(self):
        global myconn, mycur
        query=self.aQuerybox.toPlainText()
        if query == '':
            self.alog_box.addItem("ERROR: QueryBox empty!")
            print('\a')
        else:
            text=self.aQuerybox.toPlainText()
            words=text.split()
            if words[0].lower()=='alter' and words[1].lower()=='table' and words[3].lower()=='add':
                try:
                    mycur.execute(query)
                    myconn.commit()
                    print('Add_Table: Query Executed Successfully!')
                    self.alog_box.addItem('Add_Table: Query Executed Successfully!')
                    self.aQuerybox.clear()
                    self.primaryKey_checker()
                    
                except Exception as E:
                    print('\aERROR:',E)
                    self.alog_box.addItem("ERROR: "+ str(E))
            else:
                print('\aERROR: \'Executor\' cannot execute any other SQL command except "ALTER TABLE - ADD" command of DDL class.')
                self.alog_box.addItem('ERROR: \'Executor\' cannot execute any other SQL command except "ALTER TABLE - ADD" command of DDL class.')
                self.aQuerybox.clear()
    
    def getTB(self):
        global mycur, TB_list
        TB_list=[]  #debug list
        query2 = 'show tables'
        mycur.execute(query2)
        rs=mycur.fetchall()
        for row in rs:
            TB_list.append(row[0])
            self.aTBlistwidget.addItem(row[0])
    
    def add_newLine(self):
        self.aQuerybox.textCursor().insertText('\n')
    
    
    def selectTB(self):
        global myconn, mycur
        self.primaryKey_checker()
        item=self.aTBlistwidget.currentItem()
        text=item.text()
        DB_TB_choice[1]=text
        self.primaryKey_checker()
        self.aQuerybox.clear()
        self.aQuerybox.textCursor().insertText("alter table {} add ".format(DB_TB_choice[1]))
        self.aTB_label.setText("Selected Table:{}".format(DB_TB_choice[1]))
        self.aTB_selector_label.setText("Selected:{}".format(DB_TB_choice[1]))
      
            
    def endquery(self):
        global queryended
        queryended=True
        text=self.aQuerybox.toPlainText()
        newtext=text[:-2:1]
        self.aQuerybox.setPlainText(newtext)
       #.aQuerybox.textCursor().setPosition(QTextCursor.End)
        self.aQuerybox.append(');')
    
    def attrib_appendor(self):
        attrib_data=[]    # contains [ "datatype" , no of chars/numbers(int) ]
        attrib_DT=''
        attrib_name=self.aAttrib_txtbox.text()
        DT_length=self.alen_spinBox.value()
        #btn_grp=self.aint_btn.group()
        if attrib_name == '':
            self.alog_box.addItem('ERROR: Attribute name cannot be empty!')
            
            
        else:
            attrib_data.append(attrib_name)
            if self.aint_btn.isChecked():
                self.aint_btn.toggle()
                attrib_DT='int'
                attrib_data.append(attrib_DT)
                attrib_data.append(DT_length)
        
            elif self.astr_btn.isChecked():
                self.astr_btn.toggle()
                attrib_DT='char'
                attrib_data.append(attrib_DT)
                attrib_data.append(DT_length)
            
            elif self.afloat_btn.isChecked():
                self.afloat_btn.toggle()
                attrib_DT='decimal'
                attrib_data.append(attrib_DT)
                attrib_data.append(None)
            
            elif self.adate_btn.isChecked():
                self.adate_btn.toggle()
                attrib_DT='date'
                attrib_data.append(attrib_DT)
              
                attrib_data.append(None)
            self.aAttrib_txtbox.clear() 
            if attrib_data[1] not in ['int', 'decimal' , 'char' , 'date']:
                self.alog_box.addItem("ERROR: Please select DataType for Attribute '{}'.".format(attrib_name))
                print("\aERROR: Please select DataType for Attribute '{}'.".format(attrib_name))
            else:
                self.aint_btn.toggle()
                text=self.aQuerybox.toPlainText()
                len_text=len(text)
                words=text.split()
                print(len(words))
                if attrib_data[2]==None:
                    if len_text==0:
                        self.alog_box.addItem("ERROR: Please enter table name.")
                        print("\aERROR: Please enter table name.")
                    elif len(words)== 4 and words[0]=='alter' and words[1]=='table':
                        self.aQuerybox.append("( {} {} ,".format(attrib_data[0],attrib_data[1]))
                    elif len(words) > 4 and words[0]=='alter' and words[1]=='table':
                        self.aQuerybox.append("{} {} ,".format(attrib_data[0],attrib_data[1]))
                         
                    if self.aprimarykey_checkBox.isChecked() and self.anot_NULL_checkBox.isChecked():
                        self.aprimarykey_checkBox.toggle()
                        self.anot_NULL_checkBox.toggle()
                        self.aprimarykey_checkBox.setEnabled(False)
                        text=self.aQuerybox.toPlainText()
                        newtext=text[:-1:1]
                        self.aQuerybox.setPlainText(newtext)
                        self.aQuerybox.append('primary key not null ,')
                        
                    else:
                        if self.aprimarykey_checkBox.isChecked():
                            self.aprimarykey_checkBox.toggle()
                            self.aprimarykey_checkBox.setEnabled(False)
                            text=self.aQuerybox.toPlainText()
                            newtext=text[:-1:1]
                            self.aQuerybox.setPlainText(newtext)
                            #self.aQuerybox.textCursor().setPosition(QTextCursor.End)
                            self.aQuerybox.append('primary key ,')
                    
                        elif self.anot_NULL_checkBox.isChecked():
                            self.anot_NULL_checkBox.toggle()
                            text=self.aQuerybox.toPlainText()
                            newtext=text[:-1:1]
                            self.aQuerybox.setPlainText(newtext)
                            #self.aQuerybox.textCursor().setPosition(QTextCursor.End)
                            self.aQuerybox.append('not null ,')  
                
                else:
                    if len_text==0:
                        self.alog_box.addItem("ERROR: Please enter table name.")
                        print("\aERROR: Please enter table name.")
                    elif len(words)== 4 and words[0]=='alter' and words[1]=='table':
                        self.aQuerybox.append("({} {}({}) ,".format(attrib_data[0],attrib_data[1],attrib_data[2]))
                    elif len(words) > 4 and words[0]=='alter' and words[1]=='table':
                        self.aQuerybox.append("{} {}({}) ,".format(attrib_data[0],attrib_data[1],attrib_data[2]))
                    
                    if self.aprimarykey_checkBox.isChecked() and self.anot_NULL_checkBox.isChecked():
                        self.aprimarykey_checkBox.toggle()
                        self.anot_NULL_checkBox.toggle()
                        self.aprimarykey_checkBox.setEnabled(False)
                        text=self.aQuerybox.toPlainText()
                        newtext=text[:-1:1]
                        self.aQuerybox.setPlainText(newtext)
                        self.aQuerybox.append('primary key not null ,')
                        
                    else:
                        if self.aprimarykey_checkBox.isChecked():
                            self.aprimarykey_checkBox.toggle()
                            self.aprimarykey_checkBox.setEnabled(False)
                            text=self.aQuerybox.toPlainText()
                            newtext=text[:-1:1]
                            self.aQuerybox.setPlainText(newtext)
                            self.aQuerybox.append('primary key ,')
                    
                        elif self.anot_NULL_checkBox.isChecked():
                            self.anot_NULL_checkBox.toggle()
                            text=self.aQuerybox.toPlainText()
                            newtext=text[:-1:1]
                            self.aQuerybox.setPlainText(newtext)
                            self.aQuerybox.append('not null ,')                            
                
                        
        
        
    
    def helpPopup(self):
        print('User Clicked Add_Column to_Table:Help Btn.')
        msg="""
If you know MySQL Queries, type the column-addition-query into the textbox and 'Execute' it.

If you don't know MySQL queries, start by:
    
    1. Checking the correct Table.
    2. Go to the 'Appending Tools' tab and enter details of your first attribute.
    [These are compulsory for any MySQL table:
        a) At least one attribute.
        b) DataType and max length of characters/numbers to be
        specified clearly.]
        
        
    3. Keep adding as many attributes as you want.
    4. Set additional properties for the created datatype;
        [primary key**, not NULL]
    
    5. Click on 'End Query' and press the Execute button.
    
NOTE: Once query is executed, you cannot undo it here. Navigate to
MainMenu and go to the query page to 'Modify Column'.

** you can set only ONE attribute as primary key.
===If button is disabled but you didn't execute the query,
try re-selecting your table again.===
=== If primary key already exists, you cannot add another one.
            """
        popup=QMessageBox.about(self,'How to Use? (XXL version)',msg)
        
        

class insert_Data(QDialog):
    def __init__(self):
        super(insert_Data,self).__init__()
        loadUi('insert_DATA.ui', self)
        self.Querybox.textCursor().insertText("insert into {} values(".format(DB_TB_choice[1]))
        self.executor.clicked.connect(self.execute)
        self.display_tabWidget.setTabIcon(0,QtGui.QIcon(QtGui.QPixmap(1,1)))
        self.clearQueryBox.clicked.connect(lambda:self.Querybox.clear())
        self.selected_DB.setText(DB_TB_choice[0])
        self.selected_TB.setText(DB_TB_choice[1])
        self.display_tabWidget.currentChanged.connect(lambda:self.display_tabWidget.setTabIcon(0,QtGui.QIcon(QtGui.QPixmap(1,1))))
        self.appendorTab_enabled.clicked.connect(self.appendorTab_enabler)
        self.appendorTab_disabled.clicked.connect(self.appendorTab_enabler)
        self.fetch_attrib_metadata()
        self.int_appendor.clicked.connect(self.append_int)
        self.str_appendor.clicked.connect(self.append_str)
        self.float_appendor.clicked.connect(self.append_float)
        self.back_btn.clicked.connect(self.goBack)
        self.int_endquery.clicked.connect(self.endquery)
        self.str_endquery.clicked.connect(self.endquery)
        self.float_endquery.clicked.connect(self.endquery)
        self.date_endquery.clicked.connect(self.endquery)
        self.displayall_DATA.clicked.connect(self.displayDATA)
        self.date_appendor.clicked.connect(self.append_date)
        self.help.clicked.connect(self.help_popup)
        
    def append_date(self):
        date=self.date_calendarWidget.selectedDate()
      # date=dummy_date.text()
        print('\n',date)
        print(type(date))
        print(str(date))
        words=str(date).split()
        print(words)
        p1=words[0]    # string manipulation to extract date
                                    # from class with sh!t as F documentation
        year=p1[-5:-1:1]
        p2=words[1]
        
            
        month=p2[:-1:1]
        if len(month) == 1:
            month = '0' + p2[:-1:1]
        p3=words[2]
        day=p3[:-1:1]
        newdate="'{}-{}-{}'".format(year,month,day)
        query=self.Querybox.toPlainText()
        if len(query) == 0:
            global DB_TB_choice
            self.Querybox.append("insert into {} values({},".format(DB_TB_choice[1],newdate))
        else:
            self.Querybox.append(" {},".format(newdate))
     
    def help_popup(self):
        msg="""
If you know MySQL Queries, type the DATA-insertion-query into the textbox and 'Execute' it.

If you don't know MySQL queries, start by:
    
    1. Referring to the order of Attributes in the Attribute Table..
    2. Go to the 'Appending Tools' tab and enter data of the correct datatype of the corresponding attribute.
    [These are compulsory for any MySQL table:
        a) DataType and max length of characters/numbers to be
        followed carefully.
        b) Attributes set as "NOT NULL"  && "PRIMARY KEY" must be filled in.]
        
        
    3. Keep adding as much data as you want. Recommended to do it one at a time.   
    4. Click on 'End Query' and press the Execute button.
    
NOTE: Once query is executed, you cannot undo it here.
            """
        popup=QMessageBox.about(self,'How to Use? (XXL version)',msg)
    
    
    
        
    def displayDATA(self):
        self.Error.setText('')
        try:
            query="select * from {}".format(DB_TB_choice[1])
            mycur.execute(query)
            rs=mycur.fetchall()
            if rs == []:
                msg = "This table '{}' has no data to be displayed.".format(DB_TB_choice[1])
                popup = QMessageBox.about(self,"ERROR",msg)
            else:
                TBwin = display_table(self)
                if TBwin.exec():
                    exit
        except Exception as E:
            msg = "ERROR: " + str(E) +"\nTYPE: " +str(type(E))
            popup = QMessageBox.about(self,"ERROR",msg)
            print('\a')
    
    def appendorTab_enabler(self):
        if self.appendorTab_enabled.isChecked():
            self.input_tabWidget.setEnabled(True)
        elif self.appendorTab_disabled.isChecked():
            self.input_tabWidget.setEnabled(False)
    
    def append_float(self):
        integer=self.float_integerspinBox.value()
        fraction=self.fractional_doubleSpinBox.value()
        Value=float(integer)+float(fraction)
        query=self.Querybox.toPlainText()
        if len(query) == 0:
            global DB_TB_choice
            self.Querybox.append("insert into {} values({},".format(DB_TB_choice[1],str(Value)))
        else:
            self.Querybox.append(" {},".format(str(Value)))
    
    def append_str(self):
        text=self.str_TextEdit.toPlainText()
        query=self.Querybox.toPlainText()
        if len(query) == 0:
            if text == "" or text == None:
                print("\aERROR: Cannot append an empty string.")
                self.Error.setText("ERROR: Cannot append an empty string.")
                self.log_box.addItem("ERROR: Cannot append an empty string.")
                self.display_tabWidget.setTabIcon(0,QtGui.QIcon("warning.png"))
                
            else:
                global DB_TB_choice
                self.Error.setText("")
                self.Querybox.textCursor().insertText("insert into {} values('{}',".format(DB_TB_choice[1],text))
                self.str_TextEdit.clear()
        else:
            if text == "" or text == None:
                print("\aERROR: Cannot append an empty string.")
                self.Error.setText("ERROR: Cannot append an empty string.")
                self.log_box.addItem("ERROR: Cannot append an empty string.")
                self.display_tabWidget.setTabIcon(0,QtGui.QIcon("warning.png"))
            else:
                self.Error.setText("")
                self.Querybox.append(" '{}',".format(text))
                self.str_TextEdit.clear()
            
    
    def fetch_attrib_metadata(self):
        global DB_TB_choice, myconn, mycur
        TB=DB_TB_choice[1]
        rs=[]
        try:
            query="desc {}".format(TB)
            mycur.execute(query)
            rs=mycur.fetchall()
            rowCount=mycur.rowcount
            columnCount=None
            #print('GOT ATTRIB METADATA.')
            for row in rs:
                print(row)
                columnCount=len(row)
            self.Attrib_table.setRowCount(rowCount+1)
            self.Attrib_table.setColumnCount(columnCount+1)
            
            self.Attrib_table.setItem(0,0,QTableWidgetItem("Order (L to R)"))
            self.Attrib_table.setItem(0,1,QTableWidgetItem("Attribute Name"))
            self.Attrib_table.setItem(0,2,QTableWidgetItem("DataType"))
            self.Attrib_table.setItem(0,3,QTableWidgetItem("Null allowed?"))
            self.Attrib_table.setItem(0,4,QTableWidgetItem("Key"))
            self.Attrib_table.setItem(0,5,QTableWidgetItem("Extra"))
            self.Attrib_table.setItem(0,6,QTableWidgetItem("End of Row"))
             
            for r in range(rowCount):
                self.Attrib_table.setItem(r+1,0,QTableWidgetItem(str(r+1)))
                self.Attrib_table.setItem(r+1,6,QTableWidgetItem("End of Row"))
            for r_i in range(1,rowCount+1):
                for c_i in range(1,columnCount+1):
                    item=QTableWidgetItem(str(rs[r_i-1][c_i-1]))
                    self.Attrib_table.setItem(r_i,c_i,item)
            for j in range(columnCount+1):
                self.Attrib_table.item(0,j).setBackground(QtGui.QColor(191,239,239))
                    
            self.Attrib_table.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers) # B  I  G      B  R  A  I  N
            
        except Exception as E:
            msg="ERROR: {}".format(str(E))
            popup=QMessageBox.about(self,'INTERNAL ERROR 1',msg)
            #self.reject()
        
    def append_int(self):
        text=self.int_lineEdit.text()
        try:
            Integer=int(text)
            query=self.Querybox.toPlainText()
            if len(query) == 0:
                global DB_TB_choice
                self.Querybox.append("insert into {} values({},".format(DB_TB_choice[1],text))
                self.int_lineEdit.clear()
                self.Error.setText("")
            else:
                self.Querybox.append(" {},".format(text))
                self.int_lineEdit.clear()
                self.Error.setText("")
        except Exception as E:
            print("\aERROR: {}".format(str(E)))
            self.Error.setText("ERROR: {}".format(str(E)))
            self.log_box.addItem("ERROR: {}".format(str(E)))
            self.display_tabWidget.setTabIcon(0,QtGui.QIcon("warning.png"))
                    
    def endquery(self):
       # global queryended
        #queryended=True
        text=self.Querybox.toPlainText()
        newtext=text[:-1:1]
        self.Querybox.setPlainText(newtext)
        self.Querybox.append(');')
    
    def goBack(self):
        main=MainWindow()
        widget.addWidget(main)
        widget.setCurrentIndex(widget.currentIndex()+1)
        print(widget.currentIndex())
    
    def execute(self):
        global myconn, mycur, DB_TB_choice
        query=self.Querybox.toPlainText()
        if query == '':
            self.log_box.addItem("ERROR: QueryBox empty!")
            self.display_tabWidget.setTabIcon(0,QtGui.QIcon("warning.png"))
            print('\a')
        else:
            words=query.split()
            if words[0].lower()=='insert' and words[1].lower()=='into' and words[2].lower()== DB_TB_choice[1].lower():
                try:
                    mycur.execute(query)
                    myconn.commit()
                    print('INSERT_DATA: Query Executed Successfully!')
                    self.log_box.addItem('INSERT_DATA: Query Executed Successfully!')
                    self.display_tabWidget.setTabIcon(0,QtGui.QIcon("tick.png"))
                    self.Querybox.clear()
                
                except Exception as E:
                    print('\aERROR:',E)
                    self.log_box.addItem("ERROR: "+ str(E))
                    self.display_tabWidget.setTabIcon(0,QtGui.QIcon("warning.png"))
            else:
                print('\aERROR: \'Executor\' cannot execute any other SQL command except "INSERT" command of DML class.')
                self.log_box.addItem('ERROR: \'Executor\' cannot execute any other SQL command except "INSERT" command of DML class.')
                self.display_tabWidget.setTabIcon(0,QtGui.QIcon("warning.png"))
                self.Querybox.clear()

class Add_tb(QDialog):
    def __init__(self):
        super(Add_tb,self).__init__()
        loadUi('add_TB.ui',self)
  
        if queryended==True:
            self.endQuery.setEnabled(False)
        elif queryended==False:
            self.endQuery.setEnabled(True)
        self.execuTOR.clicked.connect(self.execute)
        self.basic_appenDOR.clicked.connect(self.init_query)
        self.basic_newline.clicked.connect(self.add_newLine)
        self.main_newline.clicked.connect(self.add_newLine)
        self.Querybox.textCursor().insertText('create table ')
        self.back_btn.clicked.connect(self.goBack)
        self.main_appenDOR.clicked.connect(self.attrib_appendor)
        self.endQuery.clicked.connect(self.endquery)
        self.help.clicked.connect(self.helpPopup)
        self.help_2.clicked.connect(self.helpPopup)
        self.tabWidget.setTabEnabled(1,False)
    
    def helpPopup(self):
        print('User Clicked Add_Table:Help Btn.')
        msg="""
If you know MySQL Queries, type the table-creation-query into the textbox and 'Execute' it.

If you don't know MySQL queries, start by appending your table name.
    
    1. Append the name of your table.
    2. Go to the 'Main' tab and enter details of your first attribute.
    [These are compulsory for any MySQL table:
        a) At least one attribute.
        b) DataType and max length of characters/numbers to be
        specified clearly.]
        
    3. Keep adding as many attributes as you want.
    4. Set additional properties for the created datatype;
        [primary key**, not NULL]
    
    5. Click on 'End Query' and press the Execute button.
    
NOTE: Once query is executed, you cannot undo it here. Navigate to
MainMenu and go to the query page to 'Modify Column'.

** you can set only ONE attribute as primary key.
===If button is disabled but you didn't execute the query,
try appending your table name again.===
            """
        popup=QMessageBox.about(self,'How to Use? (XXL version)',msg)
    
    def add_newLine(self):
        self.Querybox.textCursor().insertText('\n')
        
    def goBack(self):
        main=MainWindow()
        widget.addWidget(main)
        widget.setCurrentIndex(widget.currentIndex()+1)
        print(widget.currentIndex())
    
    
    def execute(self):
        global myconn, mycur
        query=self.Querybox.toPlainText()
        if query == '':
            self.log_box.addItem("ERROR: QueryBox empty!")
            print('\a')
        else:
            text=self.Querybox.toPlainText()
            words=text.split()
            if words[0].lower()=='create' and words[1].lower()=='table':
                try:
                    mycur.execute(query)
                    myconn.commit()
                    print('Add_Table: Query Executed Successfully!')
                    self.log_box.addItem('Add_Table: Query Executed Successfully!')
                    self.Querybox.clear()
                
                except Exception as E:
                    print('\aERROR:',E)
                    self.log_box.addItem("ERROR: "+ str(E))
            else:
                print('\aERROR: \'Executor\' cannot execute any other SQL command except "CREATE" command of DDL class.')
                self.log_box.addItem('ERROR: \'Executor\' cannot execute any other SQL command except "CREATE" command of DDL class.')
                
    
    def init_query(self):
        tb_name=self.TB_namebox.text()
        if tb_name == '':
            self.log_box.addItem("ERROR: Cannot initialize query with empty TableName.")
            print('\a')
        else:
            if len(self.Querybox.toPlainText()) != 0:
                self.Querybox.textCursor().insertText(tb_name + ' ')
                self.primarykey_checkBox.setEnabled(True)
                self.tabWidget.setTabEnabled(1,True)
                self.tabWidget.setCurrentIndex(self.tabWidget.currentIndex() + 1)
            else:
                self.Querybox.textCursor().insertText("create table {} ".format(tb_name))
                self.tabWidget.setTabEnabled(1,True)
                self.primarykey_checkBox.setEnabled(True)
                self.tabWidget.setCurrentIndex(self.tabWidget.currentIndex() + 1)
                
    def endquery(self):
        global queryended
        queryended=True
        text=self.Querybox.toPlainText()
        newtext=text[:-2:1]
        self.Querybox.setPlainText(newtext)
   
        self.Querybox.append(');')
    
    
    def attrib_appendor(self):
        attrib_data=[]
        attrib_DT=''
        attrib_name=self.Attrib_txtbox.text()
        DT_length=self.len_spinBox.value()
        
        if attrib_name == '':
            self.log_box.addItem('ERROR: Attribute name cannot be empty!')
           
            
        else:
            attrib_data.append(attrib_name)
            if self.int_btn.isChecked():
                self.int_btn.toggle()
                attrib_DT='int'
                attrib_data.append(attrib_DT)
                attrib_data.append(DT_length)
        
            elif self.str_btn.isChecked():
                self.str_btn.toggle()
                attrib_DT='char'
                attrib_data.append(attrib_DT)
                attrib_data.append(DT_length)
            
            elif self.float_btn.isChecked():
                self.float_btn.toggle()
                attrib_DT='float'
                attrib_data.append(attrib_DT)
                attrib_data.append(None)
            
            elif self.date_btn.isChecked():
                self.date_btn.toggle()
                attrib_DT='date'
                attrib_data.append(attrib_DT)
              
                attrib_data.append(None)
            self.Attrib_txtbox.clear()
        
        
            if attrib_data[1] not in ['int', 'float' , 'char' , 'date']:
                self.log_box.addItem("ERROR: Please select DataType for Attribute '{}'.".format(attrib_name))
                print("\aERROR: Please select DataType for Attribute '{}'.".format(attrib_name))
            else:
                self.int_btn.toggle()
                text=self.Querybox.toPlainText()
                len_text=len(text)
                words=text.split()
                print(len(words))
                if attrib_data[2]==None:
                    if len_text==0:
                        self.log_box.addItem("ERROR: Please enter table name.")
                        print("\aERROR: Please enter table name.")
                    elif len(words)== 3 and words[0]=='create' and words[1]=='table':
                        self.Querybox.append("( {} {} ,".format(attrib_data[0],attrib_data[1]))
                    elif len(words) > 3 and words[0]=='create' and words[1]=='table':
                        self.Querybox.append("{} {} ,".format(attrib_data[0],attrib_data[1]))
                         
                    if self.primarykey_checkBox.isChecked() and self.not_NULL_checkBox.isChecked():
                        self.primarykey_checkBox.toggle()
                        self.not_NULL_checkBox.toggle()
                        self.primarykey_checkBox.setEnabled(False)
                        text=self.Querybox.toPlainText()
                        newtext=text[:-1:1]
                        self.Querybox.setPlainText(newtext)
                        self.Querybox.append('primary key not null ,')
                        
                    else:
                        if self.primarykey_checkBox.isChecked():
                            self.primarykey_checkBox.toggle()
                            self.primarykey_checkBox.setEnabled(False)
                            text=self.Querybox.toPlainText()
                            newtext=text[:-1:1]
                            self.Querybox.setPlainText(newtext)
                            self.Querybox.append('primary key ,')
                    
                        elif self.not_NULL_checkBox.isChecked():
                            self.not_NULL_checkBox.toggle()
                            text=self.Querybox.toPlainText()
                            newtext=text[:-1:1]
                            self.Querybox.setPlainText(newtext)
                            self.Querybox.append('not null ,')  
                
                else:
                    if len_text==0:
                        self.log_box.addItem("ERROR: Please enter table name.")
                        print("\aERROR: Please enter table name.")
                    elif len(words)== 3 and words[0]=='create' and words[1]=='table':
                        self.Querybox.append("({} {}({}) ,".format(attrib_data[0],attrib_data[1],attrib_data[2]))
                    elif len(words) > 3 and words[0]=='create' and words[1]=='table':
                        self.Querybox.append("{} {}({}) ,".format(attrib_data[0],attrib_data[1],attrib_data[2]))
                    
                    if self.primarykey_checkBox.isChecked() and self.not_NULL_checkBox.isChecked():
                        self.primarykey_checkBox.toggle()
                        self.not_NULL_checkBox.toggle()
                        self.primarykey_checkBox.setEnabled(False)
                        text=self.Querybox.toPlainText()
                        newtext=text[:-1:1]
                        self.Querybox.setPlainText(newtext)
                        self.Querybox.append('primary key not null ,')
                        
                    else:
                        if self.primarykey_checkBox.isChecked():
                            self.primarykey_checkBox.toggle()
                            self.primarykey_checkBox.setEnabled(False)
                            text=self.Querybox.toPlainText()
                            newtext=text[:-1:1]
                            self.Querybox.setPlainText(newtext)
                            self.Querybox.append('primary key ,')
                    
                        elif self.not_NULL_checkBox.isChecked():
                            self.not_NULL_checkBox.toggle()
                            text=self.Querybox.toPlainText()
                            newtext=text[:-1:1]
                            self.Querybox.setPlainText(newtext)
                            self.Querybox.append('not null ,')                            
                
                        
class modify_tb_column(QDialog):
    def __init__(self):
        super(modify_tb_column,self).__init__()
        loadUi('modify_TB_column.ui',self)
        self.executor.clicked.connect(self.execute)
        self.display_tabWidget.setTabIcon(0,QtGui.QIcon(QtGui.QPixmap(1,1)))
        self.appendor.clicked.connect(self.attrib_appendor)
        self.fetch_attributes()
        self.Desc_Table()
        self.primaryKey_checker()
        self.back_btn.clicked.connect(self.goBack)
        self.display_tabWidget.currentChanged.connect(lambda:self.display_tabWidget.setTabIcon(0,QtGui.QIcon(QtGui.QPixmap(1,1))))
        self.col_listWidget.itemClicked.connect(self.getColumn)
        self.input_tabWidget.setTabEnabled(1,False)
        self.rm_primaryKey.clicked.connect(self.removePrimaryKey)
        
    def removePrimaryKey(self):
        self.Querybox.clear()
        query="alter table {} drop primary key;".format(DB_TB_choice[1])
        self.Querybox.append(query)
        self.rm_primaryKey.setEnabled(False)
    
    
    def primaryKey_checker(self):
        global DB_TB_choice, myconn, mycur
        try:
            query="desc {}".format(DB_TB_choice[1])
            mycur.execute(query)
            rs=mycur.fetchall()
            for row in rs:
                if row[3].upper() == 'PRI':
                    self.primarykey_checkBox.setEnabled(False)
                    return True
            else:
                self.rm_primaryKey.setEnabled(True)
                self.primarykey_checkBox.setEnabled(True)
                return False
        except Exception as E:
            msg="ERROR: " + str(E)
            popup=QMessageBox.about(self,"INTERNAL ERROR",msg)
            print("\aERROR: " + str(E))
    
    def getColumn(self):
        global DB_TB_choice, col_TBM
        self.Querybox.clear()
        item=self.col_listWidget.currentItem()
        col_TBM=item.text()
        self.Querybox.textCursor().insertText("alter table {} modify {}".format(DB_TB_choice[1],col_TBM))
        self.selector_selected_Col.setText("Selected: {}".format(col_TBM))
        self.input_tabWidget.setTabEnabled(1,True)
        self.primaryKey_checker()
        self.selected_Col.setText(col_TBM)
        self.selected_TB.setText(DB_TB_choice[1])
       
        
            
    
    def goBack(self):
        main=MainWindow()
        widget.addWidget(main)
        widget.setCurrentIndex(widget.currentIndex()+1)
        print(widget.currentIndex())
    
    
    
    def fetch_attributes(self):
        global DB_TB_choice, myconn, mycur
        self.col_listWidget.clear()
        try:
            query="desc {}".format(DB_TB_choice[1])
            mycur.execute(query)
            rs=mycur.fetchall()
            if rs == []:
                msg="No column found to modify in this table."
                popup=QMessageBox.about(self,"Alert",msg)
                print('\a',msg)
            else:
                for row in rs:
                    self.col_listWidget.addItem(row[0])
                print('Fetched all Columns.')
        except Exception as E:
            Msg="Error: {}".format(str(E))
            popup=QMessageBox.about(self,"INITIALIZATION ERROR",msg)
            print(msg,'\n\a')
    
    def execute(self):
        global myconn, mycur
        query=self.Querybox.toPlainText()
        if query == '':
            self.log_box.addItem("ERROR: QueryBox empty!")
            self.display_tabWidget.setTabIcon(0,QtGui.QIcon('warning.png'))
            print('\a')
        else:
            words=query.split()
            if words[0].lower()=='alter' and words[1].lower()=='table':
                try:
                    mycur.execute(query)
                    myconn.commit()
                    print('Modify_Column: Query Executed Successfully!')
                    self.log_box.addItem('Modify_Column: Query Executed Successfully!')
                    self.Querybox.clear()
                    self.display_tabWidget.setCurrentIndex(self.display_tabWidget.currentIndex() - 1)
                    self.display_tabWidget.setTabIcon(0,QtGui.QIcon("tick.png"))
                    self.primaryKey_checker()
                    self.Desc_Table()
                    self.log_box.addItem('Modify_Column: Updated Table Description.')
                    
                    print('\a')
                    
                except Exception as E:
                    print('\aERROR:',E)
                    self.log_box.addItem("ERROR: "+ str(E))
                    self.display_tabWidget.setTabIcon(0,QtGui.QIcon('warning.png'))
                    
                


            else:
                print('\aERROR: \'Executor\' cannot execute any other SQL command except "ALTER TABLE - MODIFY" command of DDL class.')
                self.log_box.addItem('ERROR: \'Executor\' cannot execute any other SQL command except "ALTER TABLE - MODIFY" command of DDL class.')
                self.display_tabWidget.setTabIcon(0,QtGui.QIcon('warning.png'))
    
    
    def Desc_Table(self):
        global DB_TB_choice, myconn, mycur
        TB=DB_TB_choice[1]
        rs=[]
        try:
            query="desc {}".format(TB)
            mycur.execute(query)
            rs=mycur.fetchall()
            rowCount=mycur.rowcount
            columnCount=None
            #print('GOT ATTRIB METADATA.')
            for row in rs:
                print(row)
                columnCount=len(row)
                break
            self.tableWidget.setRowCount(rowCount+1)
            self.tableWidget.setColumnCount(columnCount+1)
            
            self.tableWidget.setItem(0,0,QTableWidgetItem("Sl No"))
            self.tableWidget.setItem(0,1,QTableWidgetItem("Attribute Name"))
            self.tableWidget.setItem(0,2,QTableWidgetItem("DataType"))
            self.tableWidget.setItem(0,3,QTableWidgetItem("Null allowed?"))
            self.tableWidget.setItem(0,4,QTableWidgetItem("Key"))
            self.tableWidget.setItem(0,5,QTableWidgetItem("Default"))
            self.tableWidget.setItem(0,6,QTableWidgetItem("Extra"))
           
             
            for r in range(rowCount):
                self.tableWidget.setItem(r+1,0,QTableWidgetItem(str(r+1)))
               # self.Attrib_table.setItem(r+1,6,QTableWidgetItem("End of Row"))
            for r_i in range(1,rowCount+1):
                for c_i in range(1,columnCount):
                    item=QTableWidgetItem(str(rs[r_i-1][c_i-1]))
                    self.tableWidget.setItem(r_i,c_i,item)
            for j in range(columnCount+1):
                self.tableWidget.item(0,j).setBackground(QtGui.QColor(191,239,239))
                    
            self.tableWidget.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers) # B  I  G      B  R  A  I  N
            
        except Exception as E:
            msg="ERROR: {}".format(str(E))
            popup=QMessageBox.about(self,'INTERNAL ERROR 1',msg)
            #self.reject()
    
    def attrib_appendor(self):
        global DB_TB_choice, col_TBM
        self.input_tabWidget.setTabEnabled(1,False)
        self.input_tabWidget.setCurrentIndex(self.input_tabWidget.currentIndex() - 1)
        self.selector_selected_Col.setText("Selected: <none>")
        attrib_data=[]
        attrib_DT=None
        text=self.Querybox.toPlainText()
        words=text.split()
        DT_length=self.len_spinBox.value()
        if self.int_btn.isChecked():
            attrib_DT='int'
            attrib_data.append(attrib_DT)
            attrib_data.append(DT_length)
        elif self.str_btn.isChecked():
            attrib_DT='char'
            attrib_data.append(attrib_DT)
            attrib_data.append(DT_length)
        elif self.float_btn.isChecked():
            attrib_DT='float'
            attrib_data.append(attrib_DT)
            attrib_data.append(None)
        elif self.date_btn.isChecked():
            attrib_DT='date'
            attrib_data.append(attrib_DT)
            attrib_data.append(None)
        if len(words)<4:
            self.log_box.addItem("ERROR!: Please select/re-select the attribute.")
            print("\aERROR: Please select/re-select the attribute.")
            self.display_tabWidget.setTabIcon(0,QtGui.QIcon('warning.png'))
        else:
            if attrib_data[1] == None:
                self.Querybox.append("{}  ;".format(attrib_data[0]))
                if self.primarykey_checkBox.isChecked() and self.not_NULL_checkBox.isChecked():
                    self.primarykey_checkBox.toggle()
                    self.not_NULL_checkBox.toggle()
                    self.primarykey_checkBox.setEnabled(False)
                    text=self.Querybox.toPlainText()
                    new_Text=text[:-2:1]
                    self.Querybox.setText(new_Text)
                    self.Querybox.append("primary key not null  ;")
                else:
                    if self.primarykey_checkBox.isChecked():
                        self.primarykey_checkBox.toggle()
                   
                        self.primarykey_checkBox.setEnabled(False)
                        text=self.Querybox.toPlainText()
                        new_Text=text[:-2:1]
                        self.Querybox.setText(new_Text)
                        self.Querybox.append("primary key  ;")
                    elif self.not_NULL_checkBox.isChecked():
                        self.not_NULL_checkBox.toggle()
                        text=self.Querybox.toPlainText()
                        new_Text=text[:-2:1]
                        self.Querybox.setText(new_Text)
                        self.Querybox.append("not null  ;")
            else:
                self.Querybox.append("{}({})  ;".format(attrib_data[0],attrib_data[1]))
                if self.primarykey_checkBox.isChecked() and self.not_NULL_checkBox.isChecked():
                    self.primarykey_checkBox.toggle()
                    self.not_NULL_checkBox.toggle()
                    self.primarykey_checkBox.setEnabled(False)
                    text=self.Querybox.toPlainText()
                    new_Text=text[:-2:1]
                    self.Querybox.setText(new_Text)
                    self.Querybox.append("primary key not null  ;")
                else:
                    if self.primarykey_checkBox.isChecked():
                        self.primarykey_checkBox.toggle()
                   
                        self.primarykey_checkBox.setEnabled(False)
                        text=self.Querybox.toPlainText()
                        new_Text=text[:-2:1]
                        self.Querybox.setText(new_Text)
                        self.Querybox.append("primary key ;")
                    
                    elif self.not_NULL_checkBox.isChecked():
                        self.not_NULL_checkBox.toggle()
                        text=self.Querybox.toPlainText()
                        new_Text=text[:-2:1]
                        self.Querybox.setText(new_Text)
                        self.Querybox.append("not null  ;")
        
                    
                    
            
            
            


        
        
            


    
#__main__
            

print('Program Console now active.')
app = QApplication(sys.argv)
welcome=wel_Login_scr()




widget = QtWidgets.QStackedWidget()
widget.addWidget(welcome)
widget.setFixedHeight(600)
widget.setFixedWidth(800)
widget.show()
try:
    sys.exit(app.exec_())
except:
    print("Exiting...")
    
#  the end  
