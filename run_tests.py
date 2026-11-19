"""Genera evidencia real sin asignar resultados manualmente."""
import json
import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

class EvidenceResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.records=[]
    def addSuccess(self,test):super().addSuccess(test);self.records.append({'test':test.id(),'status':'Aprobada'})
    def addFailure(self,test,err):super().addFailure(test,err);self.records.append({'test':test.id(),'status':'Fallida','detail':self._exc_info_to_string(err,test)})
    def addError(self,test,err):super().addError(test,err);self.records.append({'test':test.id(),'status':'Fallida','detail':self._exc_info_to_string(err,test)})
    def addSkip(self,test,reason):super().addSkip(test,reason);self.records.append({'test':test.id(),'status':'Bloqueada','detail':reason})

if __name__=='__main__':
    output=Path('test-results-local');output.mkdir(exist_ok=True)
    with (output/'execution.txt').open('w',encoding='utf-8') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=EvidenceResult).run(unittest.defaultTestLoader.discover('tests'))
    report={'executed_at_utc':datetime.now(timezone.utc).isoformat(),'engine':'mysql' if os.getenv('TEST_MYSQL')=='1' else 'sqlite',
        'scope':'Integración HTTP con cliente Flask, servicios, documentos y base de datos. No automatización de navegador.',
        'python':sys.version,'tests_run':result.testsRun,'passed':result.wasSuccessful(),'records':result.records}
    (output/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    sys.exit(0 if result.wasSuccessful() else 1)
