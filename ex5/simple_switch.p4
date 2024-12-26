#include <core.p4>
#include <v1model.p4>

const bit<16> TYPE_IPV4 = 0x800;

const bit<8> IPV4_TCP=(bit<8>)6;

/*************************************************************************
*********************** H E A D E R S  ***********************************
*************************************************************************/

typedef bit<9>  egressSpec_t;
typedef bit<48> macAddr_t;
typedef bit<32> ip4Addr_t;

header ethernet_t {
    macAddr_t dstAddr;
    macAddr_t srcAddr;
    //TO-DO: Define the EtherType header
    bit<16> etherType;
}

header ipv4_t {
    //TO-DO: Define the IPv4 header with all its fields
    bit<4>   version;
    bit<4>   ihl;
    bit<8>   diffserv;
    bit<16>  totalLen;
    bit<16>  identification;
    bit<3>   flags;
    bit<13>  fragOffset;
    bit<8>   ttl;
    bit<8>   protocol;
    bit<16>  hdrChecksum;
    bit<32>  srcAddr;
    bit<32>  dstAddr;
}

header tcp_t {
    //TO-DO: Define the TCP header with all its fields
    bit<16> src_port;
    bit<16> dst_port;
    bit<32> seq_no;
    bit<32> ack_no;
    bit<4>  data_offset;
    bit<3>  res;
    bit<3>  ecn;
    bit<1>  urg;
    bit<1>  ack;
    bit<1>  psh;
    bit<1>  rst;
    bit<1>  syn;
    bit<1>  fin;
    bit<16> window;
    bit<16> checksum;
    bit<16> urgent_ptr;
}


// We have three fields in the custom metadata structure. These values will
// be used for the codification of the feature values
struct metadata {
     bit<14> action_select1;
     bit<14> action_select2;
     bit<14> action_select3;
}

struct headers {
    ethernet_t ethernet;
    ipv4_t ipv4;
    tcp_t tcp;
}

/*************************************************************************
*********************** P A R S E R  ***********************************
*************************************************************************/

parser MyParser(packet_in packet,
                out headers hdr,
                inout metadata meta,
                inout standard_metadata_t standard_metadata) {

    state start {
        transition parse_ethernet;
    }

    state parse_ethernet {
        packet.extract(hdr.ethernet);
        transition select(hdr.ethernet.etherType) {
            TYPE_IPV4: parse_ipv4;
            default: accept;
        }
    }

   state parse_ipv4 {
        packet.extract(hdr.ipv4);
        transition select(hdr.ipv4.protocol) {
	    /* 
		TO-DO: define two transitions as follows:
		- If the packet is an IP packet, then transition to the 
		  parse_tcp state.
		- Otherwise, simply accept the packet.
	    */
	    IPV4_TCP: parse_tcp;
            default: accept;
    	}
    }
    state parse_tcp {
        packet.extract(hdr.tcp);
        transition accept;
}
}

/*************************************************************************
************   C H E C K S U M    V E R I F I C A T I O N   *************
*************************************************************************/

control MyVerifyChecksum(inout headers hdr, inout metadata meta) {   
    apply {  }
}


/*************************************************************************
**************  I N G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyIngress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {

    action drop() {
        mark_to_drop(standard_metadata);
    }

    action send_to_cpu() {
        standard_metadata.egress_spec = 255;
    }

    action clone_to_cpu() {
        clone_preserving_field_list(CloneType.I2E, 99,1);
    }

    table acl_table {
        key = {
            standard_metadata.ingress_port: ternary;
            hdr.ethernet.dstAddr:          ternary;
            hdr.ethernet.srcAddr:          ternary;
            hdr.ethernet.etherType:        ternary;
        }
        actions = {
            send_to_cpu;
            clone_to_cpu;
            drop;
        }
        @name("acl_table_counter")
        counters = direct_counter(CounterType.packets_and_bytes);
    }
    
    action ipv4_forward(macAddr_t dstAddr, egressSpec_t port) {
        standard_metadata.egress_spec = port;
        hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;
        hdr.ethernet.dstAddr = dstAddr;
    }

   action set_actionselect1(bit<14> featurevalue1){
        meta.action_select1 = featurevalue1 ;
   }

   action set_actionselect2(bit<14> featurevalue2){
        meta.action_select2 = featurevalue2 ;
   }

   action set_actionselect3(bit<14> featurevalue3){
	// TO-DO: Define the behavior of this action.
	// the action_select3 of the custom metadata
	// must be set to the value passed as argument
	meta.action_select3 = featurevalue3 ;
   }
 
   table feature1_exact{
        key = {
            hdr.ipv4.protocol : range ;
        }
        actions = {
	   NoAction;
            set_actionselect1;
        }
        size = 1024;
	@name("feature1_table_counter")
        counters = direct_counter(CounterType.packets_and_bytes);

   }

   table feature2_exact{
       key = {
           hdr.tcp.src_port : range ;
       }
       actions = {
          NoAction;
           set_actionselect2;
       }
       size = 1024;
       @name("feature2_table_counter")
       counters = direct_counter(CounterType.packets_and_bytes);

   }

    table feature3_exact{
        key = {
	    // TO-DO: Define the key using the TCP destination port.
	    // Remember the match type must be range
            hdr.tcp.dst_port : range ;
        }
        actions = {
	   NoAction;
            set_actionselect3;
        }
        size = 1024;
        @name("feature3_table_counter")
        counters = direct_counter(CounterType.packets_and_bytes);

    }

    
    
    table ipv4_exact {
        key = {
            meta.action_select1: range;
            meta.action_select2: range;
            meta.action_select3: range;
        }
        actions = {
            ipv4_forward;
            drop;
            NoAction;
        }
        size = 1024;
        default_action = drop();
        @name("ipv4_exact_table_counter")
        counters = direct_counter(CounterType.packets_and_bytes);
    }
    
    apply {
        if (hdr.ipv4.isValid() ) {
		feature1_exact.apply();
		/* 
		   TO-DO: Implement the following:
		   - If the packet is an TCP packet:
			- Try to match against the table for feature 2
			- Try to match against the table for feature 3
			Hint: Remember that the method to trying the match
			against a table is the apply() method.
		   - Otherwise:
			- Set the action for feature 1 as 1
			- Set the action for feature 2 as 1
			Hint: Remember that the action for features is
			selected through the fields of the metadata struct.
		*/
		if (hdr.ipv4.protocol == IPV4_TCP) {
                        feature2_exact.apply();
                        feature3_exact.apply();
                } else {
                        set_actionselect1(1);
                        set_actionselect2(1);
                }
	}
	ipv4_exact.apply();
	acl_table.apply();
    }
}

/*************************************************************************
****************  E G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {
    apply {  }
}

/*************************************************************************
*************   C H E C K S U M    C O M P U T A T I O N   **************
*************************************************************************/

control MyComputeChecksum(inout headers  hdr, inout metadata meta) {
     apply {
	update_checksum(
	    hdr.ipv4.isValid(),
            { hdr.ipv4.version,
	      hdr.ipv4.ihl,
              hdr.ipv4.diffserv,
              hdr.ipv4.totalLen,
              hdr.ipv4.identification,
              hdr.ipv4.flags,
              hdr.ipv4.fragOffset,
              hdr.ipv4.ttl,
              hdr.ipv4.protocol,
              hdr.ipv4.srcAddr,
              hdr.ipv4.dstAddr },
            hdr.ipv4.hdrChecksum,
            HashAlgorithm.csum16);
    }
}

/*************************************************************************
***********************  D E P A R S E R  *******************************
*************************************************************************/

control MyDeparser(packet_out packet, in headers hdr) {
    apply {
        packet.emit(hdr.ethernet);
        packet.emit(hdr.ipv4);
        packet.emit(hdr.tcp);
    }
}

/*************************************************************************
***********************  S W I T C H  *******************************
*************************************************************************/

V1Switch(
    MyParser(),
    MyVerifyChecksum(),
    MyIngress(),
    MyEgress(),
    MyComputeChecksum(),
    MyDeparser()
) main;
