simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.feature1_exact MyIngress.set_actionselect1 0x0->0x20 => 1 1";

simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.feature2_exact MyIngress.set_actionselect2 0x0->0xB => 1 1";
simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.feature2_exact MyIngress.set_actionselect2 0xC->0x568D => 2 1";
simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.feature2_exact MyIngress.set_actionselect2 0x568E->0x5BD1 => 3 1";
simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.feature2_exact MyIngress.set_actionselect2 0x5BD2->0xA8A6 => 4 1";
simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.feature2_exact MyIngress.set_actionselect2 0xA8A7->0xC30A => 5 1";
simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.feature2_exact MyIngress.set_actionselect2 0xC30B->0xFFFF => 6 1";

simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.feature3_exact MyIngress.set_actionselect3 0x0->0x1797 => 1 1";
simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.feature3_exact MyIngress.set_actionselect3 0x1798->0x23B8 => 2 1";
simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.feature3_exact MyIngress.set_actionselect3 0x23B9->0x568D => 3 1";
simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.feature3_exact MyIngress.set_actionselect3 0x568E->0xFFFF => 4 1";

simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.ipv4_exact MyIngress.ipv4_forward 1->1 1->1 1->4 => 0x0A000102 2 1";
simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.ipv4_exact MyIngress.ipv4_forward 1->1 2->3 1->1 => 0x0A000100 0 1";
simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.ipv4_exact MyIngress.ipv4_forward 1->1 4->5 1->1 => 0x0A000104 4 1";
simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.ipv4_exact MyIngress.ipv4_forward 1->1 6->6 1->1 => 0x0A000103 3 1";
simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.ipv4_exact MyIngress.ipv4_forward 1->1 2->4 2->2 => 0x0A000104 4 1";
simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.ipv4_exact MyIngress.ipv4_forward 1->1 2->4 3->3 => 0x0A000101 1 1";
simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.ipv4_exact MyIngress.ipv4_forward 1->1 2->2 4->4 => 0x0A000101 1 1";
simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.ipv4_exact MyIngress.ipv4_forward 1->1 3->4 4->4 => 0x0A000103 3 1";
simple_switch_CLI --thrift-port 9090 <<< "table_add MyIngress.ipv4_exact MyIngress.ipv4_forward 1->1 5->6 2->4 => 0x0A000104 4 1";
