package Riolu {
    part Riolu_Definitions {
        part def Elastic {
            port e_port;
        }

        part def Vue {
            port ajax;
        }

        interface db_pull connect Vue::ajax to Elastic::e_port;
    }

    part Riolu {
        private import Riolu_Definitions::*;
        part e : Elastic;
        part vue_app : Vue;

        
    }

}

package Riolu_Views {
    private import Riolu::*;
    view Riolu_Views {
        //expose Riolu::**[@SysML::PartUsage];
        expose Riolu::e;
        expose Riolu::vue_app;
        //filter @SysML::PartUsage;
        //render Views::asTreeDiagram;
        //render Views::asInterconnectionDiagram;
    }

    view Riolu_Views2 {
        expose Riolu_Definitions::**;
        render Views::asInterconnectionDiagram;
    }
}