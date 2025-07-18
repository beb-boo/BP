import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, TextInput, TouchableOpacity, ScrollView, Alert } from 'react-native';
import { FontAwesome, Ionicons, MaterialIcons } from '@expo/vector-icons';
import { doctorPatientManageApi } from '../../api/doctorPatientManage';

export default function DoctorListScreen({ navigation, route }: { navigation: any, route: any }) {
    const [search, setSearch] = useState('');
    const [doctors, setDoctors] = useState<any[]>([]);
    const [accessRequests, setAccessRequests] = useState<any[]>([]);
    const [showRequests, setShowRequests] = useState(false);
    const [loading, setLoading] = useState(false);

    // Fetch authorized doctors
    useEffect(() => {
        fetchAuthorizedDoctors();
    }, []);

    const fetchAuthorizedDoctors = async () => {
        setLoading(true);
        try {
            const response = await doctorPatientManageApi.getAuthorizedDoctors();
            setDoctors(response.data?.authorized_doctors || []);
        } catch (error) {
            Alert.alert('Error', 'Failed to fetch authorized doctors.');
        } finally {
            setLoading(false);
        }
    };

    const handleRevoke = (doctor_id: number) => {
        Alert.alert(
            'Revoke Access',
            'Are you sure you want to revoke this doctor’s access?',
            [
                { text: 'Cancel', style: 'cancel' },
                {
                    text: 'Revoke', style: 'destructive',
                    onPress: async () => {
                        try {
                            await doctorPatientManageApi.revokeDoctorAccess(doctor_id);
                            fetchAuthorizedDoctors();
                        } catch (error) {
                            Alert.alert('Error', 'Failed to revoke access.');
                        }
                    }
                }
            ]
        );
    };

    // Fetch access requests
    const fetchAccessRequests = async () => {
        setLoading(true);
        try {
            const response = await doctorPatientManageApi.viewAccessRequests();
            setAccessRequests(response.data?.access_requests || []);
            setShowRequests(true);
        } catch (error) {
            Alert.alert('Error', 'Failed to fetch access requests.');
        } finally {
            setLoading(false);
        }
    };

    const handleApprove = async (request_id: number) => {
        try {
            await doctorPatientManageApi.approveRequest(request_id);
            fetchAccessRequests();
            fetchAuthorizedDoctors();
        } catch (error) {
            Alert.alert('Error', 'Failed to approve request.');
        }
    };

    const handleReject = async (request_id: number) => {
        try {
            await doctorPatientManageApi.rejectRequest(request_id);
            fetchAccessRequests();
        } catch (error) {
            Alert.alert('Error', 'Failed to reject request.');
        }
    };

    const filteredDoctors = doctors.filter(d =>
        d.doctor?.full_name?.toLowerCase().includes(search.toLowerCase()) ||
        (d.hospital || '').toLowerCase().includes(search.toLowerCase())
    );

    return (
        <View style={styles.container}>
            <Text style={styles.title}>Authenticate Doctor List</Text>

            {showRequests ? (
                <ScrollView style={{ flex: 1, marginTop: 8 }}>
                    <View style={styles.table}>
                        <View style={styles.tableHeader}>
                            <Text style={styles.headerCell}>Doctor</Text>
                            <Text style={styles.headerCell}>Requested At</Text>
                            <View style={{ width: 80 }} />
                        </View>
                        {accessRequests.length === 0 ? (
                            <Text style={{ textAlign: 'center', margin: 16 }}>No access requests.</Text>
                        ) : (
                            accessRequests.map((req, idx) => (
                                <View key={req.request_id} style={[styles.tableRow, idx % 2 === 1 && styles.tableRowAlt]}>
                                    <Text style={styles.cell}>{req.doctor?.full_name || '-'}</Text>
                                    <Text style={styles.cell}>{req.requested_at ? new Date(req.requested_at).toLocaleDateString() : '-'}</Text>
                                    <View style={{ flexDirection: 'row', gap: 8 }}>
                                        <TouchableOpacity style={styles.acceptBtn} onPress={() => handleApprove(req.request_id)}>
                                            <Text style={styles.acceptBtnText}>Accept</Text>
                                        </TouchableOpacity>
                                        <TouchableOpacity style={styles.rejectBtn} onPress={() => handleReject(req.request_id)}>
                                            <Text style={styles.rejectBtnText}>Reject</Text>
                                        </TouchableOpacity>
                                    </View>
                                </View>
                            ))
                        )}
                    </View>
                </ScrollView>
            ) : (
                <ScrollView horizontal={false} style={{ flex: 1 }}>
                    <View style={styles.table}>
                        <View style={styles.tableHeader}>
                            <Text style={styles.headerCell}>Full name</Text>
                            <View style={{ width: 32 }} />
                        </View>
                        {filteredDoctors.map((doc, idx) => (
                            <View
                                key={doc.relation_id || doc.id}
                                style={[styles.tableRow, idx % 2 === 1 && styles.tableRowAlt]}
                            >
                                <Text style={styles.cell}>{doc.doctor?.full_name || '-'}</Text>
                                <TouchableOpacity onPress={() => handleRevoke(doc.doctor?.id)}>
                                    <MaterialIcons name="remove-circle" size={22} color="#e74c3c" />
                                </TouchableOpacity>
                            </View>
                        ))}
                    </View>

                </ScrollView>
            )}

            {showRequests ? (
                <TouchableOpacity style={styles.closeBtn} onPress={() => setShowRequests(false)}>
                    <Text style={styles.closeBtnText}>Close</Text>
                </TouchableOpacity>
            ) : (
                <TouchableOpacity style={styles.requestBtn} onPress={fetchAccessRequests}>
                    <Text style={styles.requestBtnText}>View Access Requests</Text>
                </TouchableOpacity>
            )}


            <View style={styles.bottomBar}>
                <TouchableOpacity style={styles.bottomBarIcon} onPress={() => navigation.navigate('Home')}>
                    <Ionicons name="home" size={28} color="#fff" />
                </TouchableOpacity>
                <TouchableOpacity style={styles.bottomBarIcon} onPress={() => navigation.navigate('Camera')}>
                    <Ionicons name="scan" size={28} color="#fff" />
                </TouchableOpacity>
                <TouchableOpacity style={styles.bottomBarIcon} >
                    <FontAwesome name="medkit" size={28} color="#1ccfc0" />
                </TouchableOpacity>
                <TouchableOpacity style={styles.bottomBarIcon} onPress={() => navigation.navigate("Account")}>
                    <Ionicons name="person-circle-outline" size={28} color="#fff" />
                </TouchableOpacity>
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#fff',
        paddingHorizontal: 20,
        paddingTop: 36,
    },
    title: {
        fontSize: 26,
        fontWeight: 'bold',
        marginBottom: 40,
        color: '#111',
        marginTop: 20,
    },
    searchContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#fff',
        borderRadius: 24,
        borderWidth: 1,
        borderColor: '#ccc',
        paddingHorizontal: 16,
        marginBottom: 16,
        height: 44,
    },
    searchInput: {
        flex: 1,
        fontSize: 16,
        color: '#222',
    },
    searchIcon: {
        marginLeft: 8,
    },
    sectionTitle: {
        fontSize: 16,
        fontWeight: 'bold',
        marginBottom: 8,
        color: '#111',
    },
    requestBtn: {
        alignSelf: 'center',
        backgroundColor: '#1de9d6',
        borderRadius: 16,
        paddingHorizontal: 16,
        paddingVertical: 16,
        marginBottom: 16,
        bottom: 100
    },
    requestBtnText: {
        color: '#111',
        fontWeight: 'bold',
        fontSize: 15,
    },
    table: {
        borderWidth: 1,
        borderColor: '#111',
        borderRadius: 16,
        overflow: 'hidden',
        marginBottom: 8,
    },
    tableHeader: {
        flexDirection: 'row',
        backgroundColor: '#1de9d6',
        borderTopLeftRadius: 16,
        borderTopRightRadius: 16,
        paddingVertical: 8,
        alignItems: 'center',
    },
    headerCell: {
        flex: 1,
        fontWeight: 'bold',
        color: '#111',
        fontSize: 16,
        textAlign: 'center',
    },
    tableRow: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#fff',
        paddingVertical: 10,
        paddingHorizontal: 0,
        borderBottomWidth: 1,
        borderBottomColor: '#eee',
    },
    tableRowAlt: {
        backgroundColor: '#f6f6f6',
    },
    cell: {
        flex: 1,
        fontSize: 15,
        color: '#222',
        textAlign: 'center',
    },
    acceptBtn: {
        backgroundColor: '#1ccfc0',
        borderRadius: 8,
        paddingHorizontal: 10,
        paddingVertical: 4,
        marginRight: 4,
    },
    acceptBtnText: {
        color: '#fff',
        fontWeight: 'bold',
    },
    rejectBtn: {
        backgroundColor: '#e74c3c',
        borderRadius: 8,
        paddingHorizontal: 10,
        paddingVertical: 4,
    },
    rejectBtnText: {
        color: '#fff',
        fontWeight: 'bold',
    },
    editRow: {
        flexDirection: 'row',
        justifyContent: 'flex-end',
        alignItems: 'center',
        marginTop: 8,
        marginRight: 8,
    },
    editBtn: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    editText: {
        color: '#e74c3c',
        fontSize: 15,
        fontWeight: '500',
    },
    closeBtn: {
        alignSelf: 'center',
        backgroundColor: '#eee',
        borderRadius: 16,
        paddingHorizontal: 48,
        paddingVertical: 16,
        marginBottom: 16,
        bottom: 100
    },
    closeBtnText: {
        color: '#222',
        fontWeight: 'bold',
        fontSize: 15,
    },
    bottomBar: {
        position: "absolute",
        bottom: 16,
        left: 10,
        right: 10,
        height: 64,
        backgroundColor: "#222",
        flexDirection: 'row',
        justifyContent: 'space-around',
        alignItems: 'center',
        borderRadius: 32,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.15,
        shadowRadius: 8,
        elevation: 8,
    },
    bottomBarIcon: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
    },
    bottomBarIconActive: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'transparent',
    },
}); 