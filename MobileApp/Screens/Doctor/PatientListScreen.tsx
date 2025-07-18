import React, { useEffect, useState, useRef } from 'react';
import { View, Text, StyleSheet, TextInput, TouchableOpacity, ScrollView, Alert } from 'react-native';
import { FontAwesome, Ionicons, MaterialIcons } from '@expo/vector-icons';
import { doctorPatientManageApi } from '../../api/doctorPatientManage';

export default function PatientListScreen({ navigation, route }: { navigation: any, route: any }) {
    const [search, setSearch] = useState('');
    const [patients, setPatients] = useState<any[]>([]);
    const [accessRequests, setAccessRequests] = useState<any[]>([]);
    const [showRequests, setShowRequests] = useState(false);
    const [loading, setLoading] = useState(false);
    // --- Search bar states ---
    const [searchResults, setSearchResults] = useState<any[]>([]);
    const [searching, setSearching] = useState(false);
    const [searchError, setSearchError] = useState('');
    const searchTimeout = useRef<NodeJS.Timeout | null>(null);

    // Fetch doctor's patients
    useEffect(() => {
        fetchPatients();
    }, []);

    const fetchPatients = async () => {
        setLoading(true);
        try {
            const response = await doctorPatientManageApi.getDoctorPatients();
            setPatients(response.data?.patients || []);
        } catch (error) {
            Alert.alert('Error', 'Failed to fetch patients.');
        } finally {
            setLoading(false);
        }
    };

    // Fetch access requests
    const fetchAccessRequests = async () => {
        setLoading(true);
        try {
            const response = await doctorPatientManageApi.doctorViewAccessRequests();
            setAccessRequests(response.data?.access_requests || []);
            setShowRequests(true);
        } catch (error) {
            Alert.alert('Error', 'Failed to fetch access requests.');
        } finally {
            setLoading(false);
        }
    };

    const handleDeleteRequest = async (request_id: number) => {
        Alert.alert(
            'Delete Request',
            'Are you sure you want to delete this access request?',
            [
                { text: 'Cancel', style: 'cancel' },
                {
                    text: 'Delete', style: 'destructive',
                    onPress: async () => {
                        try {
                            await doctorPatientManageApi.deleteAccessRequest(request_id);
                            fetchAccessRequests();
                        } catch (error) {
                            Alert.alert('Error', 'Failed to delete request.');
                        }
                    }
                }
            ]
        );
    };

    // --- Search bar logic ---
    useEffect(() => {
        if (searchTimeout.current) clearTimeout(searchTimeout.current);
        if (!search.trim()) {
            setSearchResults([]);
            setSearchError('');
            return;
        }
        setSearching(true);
        setSearchError('');
        searchTimeout.current = setTimeout(async () => {
            try {
                const param = { q: search.trim(), 
                    role: 'patient', 
                    page: 1,
                    per_page: 10 }
                const response = await doctorPatientManageApi.searchUsers(param);
                setSearchResults(response.data?.users || []);
                setSearchError('');
            } catch (error: any) {
                setSearchResults([]);
                setSearchError('Search failed.');
            } finally {
                setSearching(false);
            }
        }, 400); // debounce
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [search]);

    const handleRequestAccess = async (patientId: number, patientName: string) => {
        try {
            setLoading(true);
            await doctorPatientManageApi.requestPatientAccess(patientId);
            Alert.alert('Success', `Access request sent to ${patientName}`);
        } catch (error: any) {
            Alert.alert('Error', error?.response?.data?.message || 'Failed to request access.');
        } finally {
            setLoading(false);
        }
    };

    const filteredPatients = patients.filter(p =>
        p.patient?.full_name?.toLowerCase().includes(search.toLowerCase()) ||
        (p.hospital || '').toLowerCase().includes(search.toLowerCase())
    );

    return (
        <View style={styles.container}>
            <Text style={styles.title}>Patient List</Text>
            {/* --- Search Bar --- */}
            <View style={styles.searchContainer}>
                <TextInput
                    style={styles.searchInput}
                    placeholder="Search patients by name..."
                    value={search}
                    onChangeText={setSearch}
                    autoCapitalize="none"
                />
                <Ionicons name="search" size={22} color="#888" style={styles.searchIcon} />
            </View>
            {/* --- Search Results --- */}
            {search.trim() ? (
                <View style={{ flex: 1 }}>
                    {searching && <Text style={{ textAlign: 'center', color: '#888' }}>Searching...</Text>}
                    {searchError ? <Text style={{ color: 'red', textAlign: 'center' }}>{searchError}</Text> : null}
                    {!searching && searchResults.length === 0 && !searchError && (
                        <Text style={{ textAlign: 'center', color: '#888' }}>No patients found.</Text>
                    )}
                    <ScrollView>
                        {searchResults.map((user, idx) => (
                            <View key={user.id} style={[styles.tableRow, idx % 2 === 1 && styles.tableRowAlt, { alignItems: 'center' }]}> 
                                <Text style={styles.cell}>{user.full_name || '-'}</Text>
                                <TouchableOpacity
                                    style={styles.acceptBtn}
                                    onPress={() => handleRequestAccess(user.id, user.full_name)}
                                >
                                    <Text style={styles.acceptBtnText}>Request Access</Text>
                                </TouchableOpacity>
                            </View>
                        ))}
                    </ScrollView>
                </View>
            ) : (
                <>
                    <Text style={styles.sectionTitle}>Your Patients</Text>
                    {showRequests ? (
                        <ScrollView style={{ flex: 1, marginTop: 8 }}>
                            <View style={styles.table}>
                                <View style={styles.tableHeader}>
                                    <Text style={styles.headerCell}>Patient</Text>
                                    <Text style={styles.headerCell}>Status</Text>
                                    <View style={{ width: 80 }} />
                                </View>
                                {accessRequests.length === 0 ? (
                                    <Text style={{ textAlign: 'center', margin: 16 }}>No pending requests.</Text>
                                ) : (
                                    accessRequests.map((req, idx) => (
                                        <View key={req.request_id} style={[styles.tableRow, idx % 2 === 1 && styles.tableRowAlt]}>
                                            <Text style={styles.cell}>{req.patient?.full_name || '-'}</Text>
                                            <Text style={styles.cell}>{req.status || '-'}</Text>
                                            <TouchableOpacity onPress={() => handleDeleteRequest(req.request_id)}>
                                                <MaterialIcons name="delete" size={22} color="#e74c3c" />
                                            </TouchableOpacity>
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
                                {filteredPatients.map((p, idx) => (
                                    <TouchableOpacity
                                        key={p.relation_id || p.id}
                                        style={[styles.tableRow, idx % 2 === 1 && styles.tableRowAlt]}
                                        onPress={() => navigation.navigate('record', { patientId: p.patient?.id, patientName: p.patient?.full_name })}
                                    >
                                        <Text style={styles.cell}>{p.patient?.full_name || '-'}</Text>
                                        <MaterialIcons name="chevron-right" size={22} color="#888" />
                                    </TouchableOpacity>
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
                            <Text style={styles.requestBtnText}>View Pending Access Requests</Text>
                        </TouchableOpacity>
                    )}
                </>
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